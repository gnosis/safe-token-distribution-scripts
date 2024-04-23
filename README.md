# Safe Token Distribution Scripts

## GIP-64

[Link](https://forum.gnosis.io/t/gip-64-should-gnosisdao-distribute-safe-tokens-to-incentivize-decentralizing-gnosis-chain/5896) to the DAO proposal.

## Requirements

For the given locking period, 15/02/2022 18:00:44 CET - 15/02/2023 18:00:44 CET,
we collect and process the following information in the form of CSV files:

- calculate GNOs held by validators in the locking period (active_validator_list_with_00.csv)
- calculate sGNOs by owner during the locking period (sGNO_LPs_aggregated.csv)
- calculate LGNOs in pools by owner on Ethereum Mainnet and Gnosis Chain uring the locking period (LGNO_Gnosis.csv and LGNO_Ethereum.csv)


## Calculations

Run `python3 calculations.py`.

This script will create sqlite database to handle calculations and export final allocation as a CSV file under `csv/allocations/`.