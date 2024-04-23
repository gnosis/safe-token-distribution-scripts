import sqlite3
import csv



SAFE_ALLOCATION = 9000000


connection = sqlite3.connect("allocations_step1.sql")
cursor = connection.cursor()

cursor.execute("CREATE TABLE lgno_ethereum (user varchar(255), value float);")
cursor.execute("CREATE TABLE lgno_gnosis (user varchar(255), value float);")
cursor.execute("CREATE TABLE gno_validators (user varchar(255), value float);")
cursor.execute("CREATE TABLE sgno (user varchar(255), dt text, value float);")


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
with open('csv/sGNO_LPs_aggregated.csv', 'r') as file:
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
connection.close()

safe_per_gno = SAFE_ALLOCATION / eligible_gno

print("> Eligible users: %s" % n_eligible_users)
print("> Eligible GNO: %s" % eligible_gno)
print("> 1 GNO = %f SAFE" % safe_per_gno)