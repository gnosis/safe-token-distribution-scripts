# Safe Token Distribution Scripts

## GIP-64

[Link](https://forum.gnosis.io/t/gip-64-should-gnosisdao-distribute-safe-tokens-to-incentivize-decentralizing-gnosis-chain/5896) to the DAO proposal.

This repository includes all the work around the execution of this very specific part of GIP-64:

```
Equal distribution of vested SAFE tokens to GNO holders on a monthly basis until the end of the locking period (February 15, 2023, about 0.9% of all SAFE tokens).

Eligible GNO:
- GNO in locking contracts on Ethereum and Gnosis Chain.
- GNO used by individual stakers.
- GNO/sGNO staked in the gauge on curve 
```

## Requirements

For the given locking period, 15/02/2022 18:00:44 CET - 15/02/2023 18:00:44 CET,
we collect and process the following information in the form of CSV files:

- calculate GNOs held by validators in the locking period (active_validator_list_with_00.csv)
- calculate sGNOs by owner during the locking period (sGNO_LPs_aggregated.csv)
- calculate LGNOs in pools by owner on Ethereum Mainnet and Gnosis Chain uring the locking period (LGNO_Gnosis.csv and LGNO_Ethereum.csv)

Based on the figures from above, we calculate distributions through the python script, any allocations to EOAs from Ethereum (non smart-contract wallets) are distributed onto Gnosis Chain.

## Installation

Run `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

Create a `.env` file and set the value for `ETHEREUM_RPC_URL`.


## Calculations

Run `python3 calculations.py`.

This script will create sqlite database to handle calculations and export final allocation as a CSV file under `csv/allocations/`.