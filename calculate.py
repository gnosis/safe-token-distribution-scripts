from decimal import Decimal
import sqlite3
import csv
import os

from web3 import Web3
from dotenv import load_dotenv, dotenv_values 


# load variables from .env file
load_dotenv() 


SAFE_ALLOCATION = 9000000
ETHEREUM_FINAL_ALLOCATION_FILE = "csv/allocations/Safe_token_distro_-_Ethereum.csv"
GNOSIS_FINAL_ALLOCATION_FILE = "csv/allocations/Safe_token_distro_-_Gnosis.csv"
ETHEREUM_RPC_URL = os.getenv('ETHEREUM_RPC_URL')


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

# we know that the sum of all eligible GNOs is equal to 9M SAFEs
cursor.execute("CREATE TABLE allocations_intermediate (user varchar(255), value float, chain varchar(10))")

cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'ethereum' from lgno_ethereum")
cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'gnosis' from lgno_gnosis")
cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'gnosis' from gno_validators")
cursor.execute("insert into allocations_intermediate (user, value, chain) select user, value, 'gnosis' from sgno")
connection.commit()

cursor.execute("select sum(value) from allocations_intermediate")
eligible_gno = cursor.fetchone()[0]

safe_per_gno = SAFE_ALLOCATION / eligible_gno

print("> Eligible users: %s" % n_eligible_users)
print("> Eligible GNO: %s" % eligible_gno)
print("> 1 GNO = %f SAFE" % safe_per_gno)


#==============================
# CALCULATE FINAL ALLOCATIONS
#==============================

allocation_exclusions = ["00 credentials"]

if len(allocation_exclusions) > 0:
    ethereum_query = "select user, sum(value) as user_gno, (sum(value)*1)/%f as score from allocations_intermediate where chain = \"ethereum\" and user not in (\"%s\") group by user" % (eligible_gno, ','.join(allocation_exclusions))
    gnosis_query = "select user, sum(value) as user_gno, (sum(value)*1)/%f as score from allocations_intermediate where chain = \"gnosis\" and user not in (\"%s\") group by user" % (eligible_gno, ','.join(allocation_exclusions))
else:
    ethereum_query = "select user, sum(value) as user_gno, (sum(value)*1)/%f as score from allocations_intermediate where chain = \"ethereum\" group by user" % (eligible_gno)
    gnosis_query = "select user, sum(value) as user_gno, (sum(value)*1)/%f as score from allocations_intermediate where chain = \"gnosis\" group by user" % (eligible_gno)

# Create CSV for ETHEREUM
cursor.execute(ethereum_query)
ethereum_rows = cursor.fetchall()

csv_header = ["Address", "Score", "Allocation"]

w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL))
os.makedirs(os.path.dirname(ETHEREUM_FINAL_ALLOCATION_FILE), exist_ok=True)
os.makedirs(os.path.dirname(GNOSIS_FINAL_ALLOCATION_FILE), exist_ok=True)

# Start creating Safe_token_distro_-_Gnosis.csv
gno_csv = open(GNOSIS_FINAL_ALLOCATION_FILE, 'w+', newline='')
gno_writer = csv.writer(gno_csv, delimiter=',')
gno_writer.writerow(csv_header)

# Start creating Safe_token_distro_-_Ethereum.csv
with open(ETHEREUM_FINAL_ALLOCATION_FILE, 'w+', newline='') as eth_csv:
    eth_writer = csv.writer(eth_csv, delimiter=',')
    eth_writer.writerow(csv_header)

    for row in ethereum_rows:
        score = "%.10f" % Decimal(row[2])
        allocation = row[2]*SAFE_ALLOCATION

        # check if the receiver is an actual EOA or a smart-contract account
        code = w3.eth.get_code(w3.to_checksum_address(row[0]))

        if not code or code == '0x' or len(code) < 2:
            # receiver is an EOA, move allocation to Gnosis Chain
            print("> Address %s => %s => %f SAFE" % (row[0], code, float(row[2])))
            gno_writer.writerow((row[0], score, allocation))
        else:
            eth_writer.writerow((row[0], score, allocation))


# Update CSV for GNOSIS, add allocations native to Gnosis Chain
cursor.execute(gnosis_query)
gnosis_rows = cursor.fetchall()

for row in gnosis_rows:
    score = "%.10f" % Decimal(row[2])
    allocation = row[2]*SAFE_ALLOCATION
    gno_writer.writerow((row[0], score, allocation))

connection.close()


#==============================
#    DOUBLE-CHECK SCORES
#==============================

eth_score = Decimal(0)
gno_score = Decimal(0)

file = open(ETHEREUM_FINAL_ALLOCATION_FILE, 'r')
rows = csv.reader(file)
next(rows, None)
for r in rows:
    eth_score += Decimal(r[1])


file = open(GNOSIS_FINAL_ALLOCATION_FILE, 'r')
rows = csv.reader(file)
next(rows, None)
for r in rows:
    gno_score += Decimal(r[1])

total_score = eth_score + gno_score
print("> ETH overall score: %f" % eth_score)
print("> GNO overall score: %f" % gno_score)
print("> Total score: %f " % total_score)