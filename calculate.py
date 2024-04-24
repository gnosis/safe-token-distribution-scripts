from decimal import Decimal
import sqlite3
import csv
import os

from web3 import Web3
from dotenv import load_dotenv 


# load variables from .env file
load_dotenv() 


SAFE_ALLOCATION = Decimal(9000000)
ETHEREUM_FINAL_ALLOCATION_FILE = "csv/allocations/Safe_token_distro_-_Ethereum.csv"
GNOSIS_FINAL_ALLOCATION_FILE = "csv/allocations/Safe_token_distro_-_Gnosis.csv"
ETHEREUM_RPC_URL = os.getenv('ETHEREUM_RPC_URL')
GNOSIS_RPC_URL = os.getenv('GNOSIS_RPC_URL')


connection = sqlite3.connect("allocations_step1.sql")
cursor = connection.cursor()

cursor.execute("CREATE TABLE lgno_ethereum (user varchar(255), value float);")
cursor.execute("CREATE TABLE lgno_gnosis (user varchar(255), value float);")
cursor.execute("CREATE TABLE gno_validators (user varchar(255), value float);")
cursor.execute("CREATE TABLE sgno (user varchar(255), value float);")


#=====================================
#    IMPORT CSV DATA INTO SQL
#=====================================

# LGNO ETHEREUM
with open('csv/LGNO_Ethereum.csv', 'r') as file:
    rows = csv.reader(file)
    next(rows, None)  # skip CSV headers
    insert_dml = "INSERT INTO lgno_ethereum (user, value) VALUES(?, ?)"
    cursor.executemany(insert_dml, rows)
    connection.commit()


# LGNO GNOSIS CHAIN
with open('csv/LGNO_Gnosis.csv', 'r') as file:
    rows = csv.reader(file)
    next(rows, None)  # skip CSV headers
    insert_dml = "INSERT INTO lgno_gnosis (user, value) VALUES(?, ?)"
    cursor.executemany(insert_dml, rows)
    connection.commit()


# GNO VALIDATORS
with open('csv/active_validator_list_with_00.csv', 'r') as file:
    rows = csv.reader(file)
    next(rows, None)  # skip CSV headers
    insert_dml = "INSERT INTO gno_validators (user, value) VALUES(?, ?)"
    cursor.executemany(insert_dml, rows)
    connection.commit()


# GNO VALIDATORS
with open('csv/sGNO_LPs.csv', 'r') as file:
    rows = csv.reader(file)
    next(rows, None)  # skip CSV headers
    insert_dml = "INSERT INTO sgno (user, value) VALUES(?, ?)"
    cursor.executemany(insert_dml, rows)
    connection.commit()


#====================================================================
# CALCULATE HOW MUCH GNO IN TOTAL IS ELIGIBLE TO RECEIVE SAFE TOKENS
#====================================================================

# calculate how many eligible users we have
cursor.execute("select count(*) from lgno_ethereum")
c_1 = cursor.fetchone()
cursor.execute("select count(*) from lgno_gnosis")
c_2 = cursor.fetchone()
cursor.execute("select count(*) from gno_validators")
c_3 = cursor.fetchone()
cursor.execute("select count(*) from sgno")
c_4 = cursor.fetchone()

# cursor.fetchone() returns a tuple (value,)
n_eligible_users = c_1[0] + c_2[0] + c_3[0] + c_4[0]

# List of addresses that are not receiving the "concrete" airdrop but would still be eligible for it
allocation_exclusions_not_diluted = ["00 credentials"]

# List of addresses that are not receiving the airdrop, whose tokens are distributed to rest of users 
allocations_exclusions_diluted = ["0x2686d5e477d1aaa58bf8ce598fa95d97985c7fb1", "0xfc9b67b6034f6b306ea9bd8ec1baf3efa2490394"]

# we know that the sum of all eligible GNOs is equal to 9M SAFEs
cursor.execute("CREATE TABLE allocations_intermediate (user varchar(255), value float, chain varchar(10))")

# Bring data from multiple CSVs and tables inside allocations_intermediate for further computation
if len(allocations_exclusions_diluted) > 0:
    print("> Excluding and diluting allocation for: %s" % ','.join(allocations_exclusions_diluted))
    cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'ethereum' from lgno_ethereum where lower(user) not in (\"%s\")" % (','.join(allocations_exclusions_diluted)))
    cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'gnosis' from lgno_gnosis where lower(user) not in (\"%s\")" % (','.join(allocations_exclusions_diluted)))
    cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'gnosis' from gno_validators where lower(user) not in (\"%s\")" % (','.join(allocations_exclusions_diluted)))
    cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'gnosis' from sgno where lower(user) not in (\"%s\")" % (','.join(allocations_exclusions_diluted)))
else:
    cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'ethereum' from lgno_ethereum")
    cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'gnosis' from lgno_gnosis")
    cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'gnosis' from gno_validators")
    cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'gnosis' from sgno")
connection.commit()

# Calculate amount of eligible GNO
cursor.execute("select sum(value) from allocations_intermediate")
eligible_gno = Decimal(cursor.fetchone()[0])
safe_per_gno = SAFE_ALLOCATION / eligible_gno


#==============================
# CALCULATE FINAL ALLOCATIONS
#==============================

# We calculate the "score" as the amount of eligible GNO per user divided by the overall amount of eligible GNO from all users.
allocations_query_part1 = "select user, sum(value) as user_gno, (sum(value)*1)/%f as score from allocations_intermediate where chain = \"%s\""

if len(allocation_exclusions_not_diluted) > 0:
    print("> Excluding but not diluting allocation for: %s" % ','.join(allocation_exclusions_not_diluted))
    ethereum_query = allocations_query_part1 % (eligible_gno, 'ethereum') + " and lower(user) not in (\"%s\") group by user" % (','.join(allocation_exclusions_not_diluted))
    gnosis_query = allocations_query_part1 % (eligible_gno, 'gnosis') + " and lower(user) not in (\"%s\") group by user" % (','.join(allocation_exclusions_not_diluted))
else:
    ethereum_query = allocations_query_part1 % (eligible_gno, 'ethereum')  + " group by user"
    gnosis_query = allocations_query_part1 % (eligible_gno, 'gnosis')  + " group by user"

# Create CSV for ETHEREUM
cursor.execute(ethereum_query)
ethereum_rows = cursor.fetchall()

w3_eth = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL))
w3_gno = Web3(Web3.HTTPProvider(GNOSIS_RPC_URL))
os.makedirs(os.path.dirname(ETHEREUM_FINAL_ALLOCATION_FILE), exist_ok=True)
os.makedirs(os.path.dirname(GNOSIS_FINAL_ALLOCATION_FILE), exist_ok=True)

# Start creating Safe_token_distro_-_Gnosis.csv
gno_csv = open(GNOSIS_FINAL_ALLOCATION_FILE, 'w+', newline='')
gno_writer = csv.writer(gno_csv, delimiter=',')
csv_header = ["Address", "Score", "Allocation"]
gno_writer.writerow(csv_header)

# Start creating Safe_token_distro_-_Ethereum.csv
with open(ETHEREUM_FINAL_ALLOCATION_FILE, 'w+', newline='') as eth_csv:
    eth_writer = csv.writer(eth_csv, delimiter=',')
    eth_writer.writerow(csv_header)

    for row in ethereum_rows:
        score = "%.10f" % Decimal(row[2])
        allocation = Decimal(row[2])*SAFE_ALLOCATION
        allocate_to_gno = False
        # check if the receiver is an actual EOA or a smart-contract account
        code = w3_eth.eth.get_code(w3_eth.to_checksum_address(row[0]))

        if not code or code == '0x' or len(code) < 2:
            # receiver is an EOA, move allocation to Gnosis Chain if the address
            # is not a contract on Gnosis Chain side, otherwise keep on Ethereum side.
            print("> Address %s => %s => %f SAFE" % (row[0], code, float(row[2])))
            # Check if the address is not a contract on Gnosis Chain side
            code_gno = w3_gno.eth.get_code(w3_gno.to_checksum_address(row[0]))
            if not code_gno or code_gno == '0x' or len(code_gno) < 2:
                allocate_to_gno = True
            else:
                print("> Address %s is a contract on Gnosis Chain" % row[0])

        if allocate_to_gno:
            gno_writer.writerow((row[0], score, allocation))
        else:
            eth_writer.writerow((row[0], score, allocation))


# Update CSV for GNOSIS, add allocations native to Gnosis Chain
cursor.execute(gnosis_query)
gnosis_rows = cursor.fetchall()

for row in gnosis_rows:
    score = "%.10f" % Decimal(row[2])
    allocation = Decimal(row[2])*SAFE_ALLOCATION
    gno_writer.writerow((row[0], score, allocation))

connection.close()


#==============================
#    DOUBLE-CHECK SCORES
#==============================

check_eth_score = Decimal(0)
check_gno_score = Decimal(0)

file = open(ETHEREUM_FINAL_ALLOCATION_FILE, 'r')
rows = csv.reader(file)
next(rows, None)
for r in rows:
    check_eth_score += Decimal(r[1])


file = open(GNOSIS_FINAL_ALLOCATION_FILE, 'r')
rows = csv.reader(file)
next(rows, None)
for r in rows:
    check_gno_score += Decimal(r[1])

check_total_score = check_eth_score + check_gno_score

print("============= STATS =============")
print("> Eligible users: %s" % n_eligible_users)
print("> Eligible GNO: %s" % eligible_gno)
print("> 1 GNO = %f SAFE" % safe_per_gno)
print("> ETH overall score: %f" % check_eth_score)
print("> GNO overall score: %f" % check_gno_score)
print("> Total score: %f " % check_total_score)
print("=================================")