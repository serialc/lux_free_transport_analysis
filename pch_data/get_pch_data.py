from bs4 import BeautifulSoup
import urllib.parse, requests, re, os, sys, time
from datetime import datetime, date, timedelta
from pathlib import Path

# debugging
#import logging, http.client

##### Check aguments to determine mode
mode = 'full'
if len(sys.argv) >= 2:
    if sys.argv[1] in ['base', 'meta', 'details']:
        mode = sys.argv[1]
    else:
        exit("Unknown argument 1 provided. Only 'base', 'meta', 'details' are valid.")
elif len(sys.argv) == 3:
    if sys.argv[2] == "only":
        mode += "_only"
    else:
        exit("Unknown argument 2 provided. Only 'only' is valid.")
else:
    exit("To run provide an argument:\n" +
        "base, meta, details\n\n" +
        "A second argument can be provided to only run that particular section: only\n" +
        "Examples:\n" +
        "python3 get_pch_data.py base (will run all request groups: base, meta, details)\n" +
        "python3 get_pch_data.py base only (will run base request only)\n" +
        "python3 get_pch_data.py details only (will run details request only - as base, meta and details are sequential, the 'only' is not required here)")


##### Setting some paths/constants

# data target
# All available data for 2019 (and eventually 2020)
target_year = "2019"
target_start_date = date(2019,1,1)

# Retrieve ViewState, session and other codes and info from request to:
main_url = "http://www2.pch.etat.lu/comptage/home.jsf"
# Use it to fulfill request to target url at:
data_url = "http://www2.pch.etat.lu/comptage/poste_detail.jsf"

# Log/data files
path_data            = "data/"
path_counter_details = path_data + "counters/"
path_archive         = path_data + "archive/"
log_base_data        = path_data + "table_base_records.txt"
log_meta_data        = path_data + "table_meta_records.txt"

if not os.path.exists(path_counter_details):
    Path(path_counter_details).mkdir(parents=True, exist_ok=True)
    
if not os.path.exists(path_archive):
    Path(path_archive).mkdir(parents=True, exist_ok=True)

# globals
session_id = ''
viewstate_id = ''

# other constants
delim = "\t"

# for archives, logging
def dtnow():
    utc = datetime.utcnow()
    return(utc.strftime('%Y-%m-%d_%H-%M-%S'))

def update_session(get_soup=False):
    global session_id
    global viewstate_id

    # Retrieve welcome/info with list of counters (1/3 in hierarchy)
    main_result = requests.get(main_url)

    session_id = main_result.cookies['JSESSIONID']
    soup = BeautifulSoup(main_result.text, 'html.parser')
    viewstate_id = soup.find(id="j_id1:javax.faces.ViewState:0")['value']

    if get_soup:
        return(soup)

#####################################################################
# PART 1 - Get the base data for each counter 
#####################################################################

if mode in ['base', 'base_only']:
    # backup up base log if already exists
    if os.path.exists(log_base_data):
        os.rename(log_base_data, archive_path + dtnow() + "_" + os.path.basename(log_base_data))

    # save introductory records
    fh = open(log_base_data, "w")

    # Add table headers
    fh.write("category" + delim + "request_code" + delim + "counter_id" + delim + "site_name" + delim + "road_id" + delim + "speed_kmh" + "\n")

    # Get the basic list of counters (and update the session and viewstate ids)
    soup = update_session(get_soup=True)

    # parse the data to make it easily queryable, the html is a (structered) mess
    list_tables = soup.find_all(class_="liste_poste")

    # We only want the first 4 of the data tables
    print("Found " + str(len(list_tables)) + " tables, we only want the first 4.")
    table_headings = ["Autoroute", "Route nationale", "Chemin repris", "Piste cyclable"]

    # Go through each table
    for table_num in range(4):

        # get the proper embedded table content (skip headings)
        rows = list_tables[table_num].find("tbody").find_all("tr")
        print("Table " + table_headings[table_num] + " has " + str(len(rows)) + " elements.")

        # dig through cr (counter record)
        for cr in rows:
            # Iterating through introductory data of each counter
            cr_td = cr.find_all("td")

            # the paths to the good bits
            counter_request_code = cr_td[0].div.attrs['id'] #wrong?
            counter_request_code = re.split('{|}|\'', cr_td[0].a.attrs['onclick'])[4]
            counter_id = cr_td[0].text.split()[1]
            counter_name = cr_td[1].text.strip()
            counter_road_id = cr_td[2].text.strip()
            road_speed = cr_td[4].text.strip()

            print("Introductory data: ", counter_request_code, counter_id, counter_name, counter_road_id, road_speed)
            fh.write( table_headings[table_num] + delim + counter_request_code + delim + counter_id + delim + counter_name + delim + counter_road_id + delim + road_speed + "\n")

    fh.close()

    if mode == 'base_only':
        exit("Finished running '" + mode + "' processing exclusively.")

#####################################################################
# PART 2 - Get the metadata for each counter (second level)
#####################################################################


def get_lvl2(crc, get_soup=False):
    # hit the same url (POST), but with a request payload and headers
    headers = {"Host": "www2.pch.etat.lu", "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate", "Content-Type": "application/x-www-form-urlencoded", "Origin": "http://www2.pch.etat.lu", "DNT": "1", "Connection": "keep-alive", "Referer": "http://www2.pch.etat.lu/comptage/home.jsf", "Cookie": "JSESSIONID=" + session_id,  "Upgrade-Insecure-Requests": "1"}

    payload = [('j_idt9', 'j_idt9'), ("j_idt9:j_idt12", ''), ('javax.faces.ViewState', viewstate_id), (crc, crc)]

    sub_req_result = requests.post(main_url, headers=headers, data=payload)

    if get_soup:
        # parse this new file, use soup again
        soup = BeautifulSoup(sub_req_result.text, 'html.parser')

        return(soup)
    return None


if mode in ['base', 'meta', 'meta_only']:
    
    # need to refresh ids
    if mode == 'meta_only':
        update_session()

    # backup up meta log if already exists
    if os.path.exists(log_meta_data):
        os.rename(log_meta_data, archive_path + dtnow() + "_" + os.path.basename(log_meta_data))

    # Add table headers
    fh = open(log_meta_data, 'w')
    fh.write("category" + delim + "request_code" + delim + "counter_id" + delim + "site_name" + delim + "road_id" + delim + \
            "form2_id" + delim + "date_from" + delim + "date_until" + delim + "x" + delim + "y" + delim + "did" + delim + "ddesc\n")

    with open(log_base_data) as base_data:
        header = True
        for counter_line in base_data:
            counter_line = counter_line.strip()

            # skip first line
            if header:
                header = False
                continue

            parts = counter_line.split("\t")
            if len(parts) == 6:
                group, crc, cid, cn, croad, rspd = parts
            elif len(parts) == 5:
                # for bike paths, different
                rspd = ""
                group, crc, cid, cn, croad = parts
            else:
                print("Error, did not find expected number of parts (6 or 5)")
                exit(parts)
    
            # Details/metadata file query (2/3 in hierarchy)
            soup = get_lvl2(crc, get_soup=True)

            soup.find(id="posteId")
            form2_id = soup.find_all('form')[1].attrs['id']
            date_from = soup.find(id="posteId").find_all('strong')[2].text.strip()
            date_until = soup.find(id="posteId").find_all('strong')[3].text.strip()
            x,y =  [ re.split('=|&', soup.find('iframe').attrs['src'])[i] for i in [1,3] ]
            directions = []
            for direction in soup.find("table", id=re.compile("direction")).find_all('td'):
                directions.append([direction.input['value'], direction.text.strip()])

            while len(directions) < 3:
                directions.append(['', ''])

            print(form2_id, date_from, date_until, x,y, directions)

            # Write base and meta data to records
            root = group + delim + crc + delim + cid + delim + cn + delim + croad + delim + form2_id + delim + date_from + delim + date_until + delim + x + delim + y + delim

            # append file with a new row for each direction of record, some duplication of data but easier later when handling getting details
            for d in directions:
                fh.write(root + d[0] + delim + d[1] + "\n")

    fh.close()

    if mode == "meta_only":
        exit("Finished running '" + mode + "' processing exclusively.")

##############################################################################
# PART 3 - Get the number of hourly trips in *each* direction for each counter
##############################################################################

# 
query_counter = 0

def retrieved_dates(cid, dirid):
    dates = []
    try:
        with open(path_counter_details + cid + "_dir_" + dirid + "_cars.txt") as daily_records:
            for record in daily_records:
                dates.append(record.split("\t")[0])
    except FileNotFoundError:
        print("Counter file for counter id " + cid + " in direction " + dirid + " does not yet exist. Creating it.")

    return(dates)

def reset_ids(crc, verbose=True):
    global query_counter

    update_session()
    get_lvl2(crc)
    query_counter = 0
    if verbose:
        print("Reset SESSION and ViewState ids.")

if mode in ['base', 'meta', 'details', 'details_only']:

    # need to refresh ids
    #if mode in ['details', 'details_only']:
    #    update_session()

    # always reset session ids after 10 good requests
    zeroline = False

    # iterates through all dates for each sensor
    # open the meta table with sensors list
    with open(log_meta_data) as base_data:

        last_cid = ""
        header = True
        for counter_line in base_data:
            counter_line = counter_line.strip()

            # skip first line
            if header:
                header = False
                continue


            parts = counter_line.split("\t")
            if len(parts) == 12:
                group, crc, cid, cn, croad, f2id, date_from, date_until, x, y, dirid, dirdesc = parts
            else:
                print("Error, did not find expected number of parts (12). Found " + str(len(parts)))
                print(len(parts))
                exit(parts)
            
            print("Processing cid " + cid + ", direction " + dirid + ": ")

            # Open counter record file and retrieve the list of dates that we already have data for
            already_retrieved_dates = retrieved_dates(cid, dirid)

            # This counter has data available between (inclusive) these dates
            start_date = datetime.strptime(date_from, "%d.%m.%Y").date()
            end_date   = datetime.strptime(date_until, "%d.%m.%Y").date()

            # Do we need a full reset or just request another direction?
            if cid != last_cid:
                # get fresh IDs for this counter request and specify counter (and direction)
                reset_ids(crc)
            else:
                # query level2 (meta) to inform server that we want counter for certain direction
                get_lvl2(crc)

            last_cid = cid


            if start_date < target_start_date:
                start_date = target_start_date

            if end_date < target_start_date:
                continue # to next record

            # iterate throught dates within the range (start_date - end_date [inclusive])
            delta = timedelta(days=1)

            # count the number of submitted requests
            requests_submitted = 0

            ### Request data for each date in range
            while start_date <= end_date:

                if str(start_date) in already_retrieved_dates:
                    # we've already retrieved this record, go to next date
                    start_date += delta
                    continue

                requests_submitted += 1

                if query_counter >= 12:
                    reset_ids(crc, verbose=False)

                print(cid + "." + dirid + ": Trying to retrieve date " + str(start_date) + ". ", end="")
                time.sleep(0.15)

                headers = {"Host": "www2.pch.etat.lu", "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate", "Content-Type": "application/x-www-form-urlencoded", "Origin": "http://www2.pch.etat.lu", "DNT": "1", "Connection": "keep-alive", "Referer": "http://www2.pch.etat.lu/comptage/home.jsf", "Cookie": "JSESSIONID=" + session_id,  "Upgrade-Insecure-Requests": "1"}

                # meta request parameters, despite being variables, f2id is always the same - useless
                payload = [ (f2id, f2id),
                        (f2id + ':j_idt23', 'chart_journalier'),
                        (f2id + ':j_idt26' , 'U'),
                        (f2id + ':dateDuInputDate', start_date.strftime('%d.%m.%Y')),
                        (f2id + ':dateDuInputCurrentDate', start_date.strftime('%m/%Y')),
                        (f2id + ':dateAuInputDate', start_date.strftime('%d.%m.%Y')),
                        (f2id + ':dateAuInputCurrentDate', start_date.strftime('%m/%Y')),
                        (f2id + ':direction', dirid),
                        (f2id + ':j_idt34', 'Afficher'),
                        ('javax.faces.ViewState', viewstate_id) ]

                # DEBUGGING request
                #http.client.HTTPConnection.debuglevel = 1
                #logging.basicConfig()
                #logging.getLogger().setLevel(logging.DEBUG)
                #requests_log = logging.getLogger("requests.packages.urllib3")
                #requests_log.setLevel(logging.DEBUG)
                #requests_log.propagate = True

                details_req_result = requests.post(data_url + ";jsessionid=" + session_id, headers=headers, data=payload)

                soup = BeautifulSoup(details_req_result.text, 'html.parser')

                # retrieve the good bits
                try:
                    tr = soup.find("table", class_="tablepch").find_all("tr")
                except AttributeError:
                    #print("ERROR: Retrieved content that is not details. This happens when their server freaks out for some reason.")
                    #print("Parts:")
                    #print(parts)
                    #print("Payload:")
                    #print(payload)
                    #print("Response:")
                    #print(details_req_result.text)
                    #exit()
                    print("\nDidn't return expected data structure. Abandon this counter for now.")
                    #reset_ids(crc)
                    start_date += delta
                    break
                    #continue

                # SPLIT based on whether this is car/utility data or bicycle data
                if len(tr) == 6:
                    # Bicycles

                    # Save/write results to file
                    # BICYCLES
                    # bicycle_table_rows = [2,5]
                    bikes = [x.text for x in tr[2].find_all("td")] + [x.text for x in tr[5].find_all("td")]
                    bsum = sum([int(x) for x in bikes])
                    if bsum == 0:
                        print("\nBad data - bicycle data is all zeros.")
                        zeroline = True
                    else:
                        query_counter += 1

                    detailsfh = open(path_counter_details + cid + "_dir_" + dirid + "_bicycle.txt", 'a')
                    detailsfh.write(start_date.strftime('%Y-%m-%d') + delim + delim.join(bikes) + "\n")
                    detailsfh.close()

                elif len(tr) == 12:
                    # Vehicles 

                    # Save/write results to file
                    # UTILITY VEHICLES 
                    # utility_vehicle_table_rows = [2,8]
                    util = [x.text for x in tr[2].find_all("td")] + [x.text for x in tr[8].find_all("td")]

                    usum = sum([int(x) for x in util])
                    if usum == 0:
                        print("\nBad data - utility data is all zeros.")
                        zeroline = True

                    detailsfh = open(path_counter_details + cid + "_dir_" + dirid + "_utility.txt", 'a')
                    detailsfh.write(start_date.strftime('%Y-%m-%d') + delim + delim.join(util) + "\n")
                    detailsfh.close()

                    # CARS
                    # car_table_rows = [3,9]
                    cars = [x.text for x in tr[3].find_all("td")] + [x.text for x in tr[9].find_all("td")]
                    csum = sum([int(x) for x in cars])
                    if csum == 0:
                        print("Bad data - car data is all zeros.")
                        zeroline = True
                    else:
                        query_counter += 1

                    detailsfh = open(path_counter_details + cid + "_dir_" + dirid + "_cars.txt", 'a')
                    detailsfh.write(start_date.strftime('%Y-%m-%d') + delim + delim.join(cars) + "\n")
                    detailsfh.close()
                else:
                    # This is not a bicycle or vehicle details table, so... ?
                    print("Unknown details table format. Exiting.")
                    exit(tr)


                if zeroline:
                    zeroline = False
                    reset_ids(crc)

                print("Done.")

                # at end of while loop iterating through dates for a record, update start_date
                start_date += delta

                #exit("Do only one, then exit.")

            print("Processed " + str(requests_submitted) + " requests for cid " + cid + ", direction " + dirid + ".")
            #exit("TESTING multiple calls (all available dates) for one counter")
            # end of processing counters, and all the dates

        exit("Finished running '" + mode + "' processing exclusively.")

print("Finished processing")
