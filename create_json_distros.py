from decimal import Decimal
import csv
import json

from web3 import Web3


ETHEREUM_FINAL_ALLOCATION_FILE = "csv/allocations/Safe_token_distro_-_Ethereum.csv"
ETHEREUM_DISTRO_JSON_FILE = "csv/allocations/ethereum.initial-9m-distro.json"

GNOSIS_FINAL_ALLOCATION_FILE = "csv/allocations/Safe_token_distro_-_Gnosis.csv"
GNOSIS_DISTRO_JSON_FILE = "csv/allocations/gnosis.initial-9m-distro.json"


# convert allocated SAFE into wei format as requested by safe-token-distribution tools
# JSON structure:
# {
#     "address": amount wei
# }

# For stats purpose
allocated_eth = Decimal(0)
allocated_gno = Decimal(0)

#==========
# ETHEREUM
#==========
eth_allocation_file = open(ETHEREUM_FINAL_ALLOCATION_FILE, 'r')
eth_allocation_rows = csv.reader(eth_allocation_file)

next(eth_allocation_rows, None) # skip CSV headers

eth_distro_object = {}
eth_n_accounts = 0 # count number of accounts in JSON file
for r in eth_allocation_rows:
    # handle multiple accounts on the same file, just sum amounts
    if eth_distro_object.get(r[0], None):
        eth_distro_object[r[0]] += Web3.to_wei(r[2], 'ether')
    else:
        eth_distro_object[r[0]] = Web3.to_wei(r[2], 'ether')

    # for stats purpose
    allocated_eth += Web3.to_wei(r[2], 'ether')
    eth_n_accounts += 1

with open(ETHEREUM_DISTRO_JSON_FILE, 'w+') as eth_distro_file:
    eth_distro_file.write(json.dumps(eth_distro_object, indent=4))
    print("> Ethereum, written %d records" % eth_n_accounts)


#=========
# GNOSIS
#=========
gno_allocation_file = open(GNOSIS_FINAL_ALLOCATION_FILE, 'r')
gno_allocation_rows = csv.reader(gno_allocation_file)

next(gno_allocation_rows, None) # skip CSV headers

gno_distro_object = {}
gno_n_accounts = 0 # count number of accounts in JSON file
for r in gno_allocation_rows:
    # handle multiple accounts on the same file, just sum amounts
    if gno_distro_object.get(r[0], None):
        gno_distro_object[r[0]] += Web3.to_wei(r[2], 'ether')
    else:
        gno_distro_object[r[0]] = Web3.to_wei(r[2], 'ether')
    # for stats purpose
    allocated_gno += Web3.to_wei(r[2], 'ether')
    gno_n_accounts += 1

with open(GNOSIS_DISTRO_JSON_FILE, 'w+') as gno_distro_file:
    gno_distro_file.write(json.dumps(gno_distro_object, indent=4))
    print("> Gnosis Chain, written %d records" % gno_n_accounts)


print("> Ethereum Safe (wei): %f" % allocated_eth)
print("> Ethereum Safe (gwei): %f" % Web3.from_wei(allocated_eth, 'ether'))
print("> Gnosis Chain Safe (wei): %f" % allocated_gno)
print("> Gnosis Chain Safe (gwei): %f" % Web3.from_wei(allocated_gno, 'ether'))
print("> Total allocated Safe (wei): %f" % (allocated_eth+allocated_gno))
print("> Total allocated Safe (gwei): %f" % Web3.from_wei((allocated_eth+allocated_gno), 'ether'))