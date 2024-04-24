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

See [Queries & datasources](#queries-and-datasources) for more information on how these figures were calculated.

Based on the figures from above, we then calculate distributions through the python script, any allocations to EOAs from Ethereum (non smart-contract wallets) are distributed onto Gnosis Chain.

Users on Gnosis Chain can use the official [faucet](https://faucet.gnosischain.com) to claim a portion of xDAI to cover for fees.

## Installation

Run `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

Create a `.env` file and set the value for `ETHEREUM_RPC_URL`.


## Calculations

Run `python3 calculations.py`.

This script will create sqlite database to handle calculations and export final allocation as a CSV file under `csv/allocations/`.

### Queries and datasources

In the paragraphs below we showcase the queries that were used to extract data for the CSV files. These CSVs served as datasources to compute final allocations.

#### active_validator_list_with_00.csv

```sql
WITH 

lock_period AS (
	SELECT 
	TO_TIMESTAMP(1644944444) AT TIME ZONE 'UTC' AS start_timestamp
	,TO_TIMESTAMP(1644944444 + 31536000) AT TIME ZONE 'UTC' AS end_timestamp
),

validators AS (
	SELECT 
		f_public_key
		,f_index
		,f_activation_epoch
		,f_exit_epoch
		,CASE 
			WHEN encode(f_withdrawal_credentials, 'hex')  NOT LIKE '00%'
				THEN '0x' ||  RIGHT(encode(f_withdrawal_credentials, 'hex'), 40) 
				ELSE '00 credentials'
		END AS address
		,encode(f_withdrawal_credentials, 'hex') AS withdrawal_credentials
		,compute_timestamp_at_slot(f_activation_epoch*16) AS timestamp_activation
		,DATE_TRUNC('day',compute_timestamp_at_slot(f_activation_epoch*16)) AS activation_day
	FROM public.t_validators
	WHERE 
		--exclude stakewise
		encode(f_withdrawal_credentials, 'hex')  != '010000000000000000000000fc9b67b6034f6b306ea9bd8ec1baf3efa2490394'
),

final AS (
	SELECT 
		withdrawal_credentials
		,address
		,f_index
		,EXTRACT(EPOCH FROM (end_timestamp - GREATEST(timestamp_activation,start_timestamp) ))::INTEGER AS active_seconds
	FROM
		validators
		,lock_period
	WHERE
		timestamp_activation < end_timestamp

)

SELECT 
	address
	,CAST(SUM(active_seconds) AS NUMERIC)/31536000 AS avg_validators
FROM final
GROUP BY 1
ORDER BY 2 DESC
```

#### LGNO_Ethereum.csv

```sql
WITH 

deposit AS (
    SELECT 
        evt_block_time
        ,DATE_TRUNC('day',evt_block_time) AS evt_block_date
        ,"from" AS user
        ,CAST(value AS INT256) AS value
    FROM erc20_ethereum.evt_transfer
    WHERE
        contract_address = 0x4f8AD938eBA0CD19155a835f617317a6E788c868
        AND
        to = 0x4f8AD938eBA0CD19155a835f617317a6E788c868
        AND
        DATE_TRUNC('day',evt_block_time) >= DATE '2022-01-01'
),

withdrawal AS (
    SELECT 
        evt_block_time
        ,DATE_TRUNC('day',evt_block_time) AS evt_block_date
        ,to AS user
        ,CAST(-value AS INT256) AS value
    FROM erc20_ethereum.evt_transfer
    WHERE
        contract_address = 0x4f8AD938eBA0CD19155a835f617317a6E788c868
        AND
        "from" = 0x4f8AD938eBA0CD19155a835f617317a6E788c868
        AND
        DATE_TRUNC('day',evt_block_time) >= DATE '2022-01-01'
),

balance AS (
    SELECT * FROM deposit
    UNION ALL
    SELECT * FROM withdrawal
)

SELECT 
     user 
    ,value
FROM (
SELECT 
    user
    ,SUM(value)/1e18 AS value
FROM 
    balance
WHERE 
    evt_block_date <= DATE '2022-02-15'
GROUP BY 1
)
WHERE value != 0
ORDER BY 2 DESC
```

#### LGNO_Gnosis.csv

```sql
WITH 

deposit AS (
    SELECT 
        evt_block_time
        ,evt_block_date
        ,"from" AS user
        ,CAST(value AS INT256) AS value
    FROM erc20_gnosis.evt_transfer
    WHERE
        contract_address = 0xd4Ca39f78Bf14BfaB75226AC833b1858dB16f9a1
        AND
        to = 0xd4Ca39f78Bf14BfaB75226AC833b1858dB16f9a1
        AND
        evt_block_date >= DATE '2022-01-01'
),

withdrawal AS (
    SELECT 
        evt_block_time
        ,evt_block_date
        ,to AS user
        ,CAST(-value AS INT256) AS value
    FROM erc20_gnosis.evt_transfer
    WHERE
        contract_address = 0xd4Ca39f78Bf14BfaB75226AC833b1858dB16f9a1
        AND
        "from" = 0xd4Ca39f78Bf14BfaB75226AC833b1858dB16f9a1
        AND
        evt_block_date >= DATE '2022-01-01'
),

balance AS (
    SELECT * FROM deposit
    UNION ALL
    SELECT * FROM withdrawal
)

SELECT 
    user 
    ,value
FROM (
SELECT 
    user
    ,SUM(value)/1e18 AS value
FROM 
    balance
WHERE 
    evt_block_date <= DATE '2022-02-15'
GROUP BY 1
)
WHERE value != 0
ORDER BY 2 DESC
```

#### sGNO_LPs.csv

```sql
WITH 

inflow AS (
  SELECT
    evt_block_time
    ,evt_block_number
    ,evt_tx_hash
    ,to AS user
    ,CAST(value AS INT256) AS value
  FROM 
    erc20_gnosis.evt_transfer
  WHERE
    contract_address in (0xbdf4488dcf7165788d438b62b4c8a333879b7078,0x2686d5E477d1AaA58BF8cE598fA95d97985c7Fb1)
    AND 
    evt_block_time >= FROM_UNIXTIME(1644944444) AT TIME ZONE 'UTC'
    AND 
    evt_block_time < FROM_UNIXTIME(1644944444 + 31536000) AT TIME ZONE 'UTC'
), 

outflow AS (
  SELECT
    evt_block_time
    ,evt_block_number
    ,evt_tx_hash
    ,"from" AS user
    ,CAST(-value AS INT256) AS value
  FROM 
    erc20_gnosis.evt_transfer
  WHERE
    contract_address in (0xbdf4488dcf7165788d438b62b4c8a333879b7078,0x2686d5E477d1AaA58BF8cE598fA95d97985c7Fb1)
    AND 
    evt_block_time >= FROM_UNIXTIME(1644944444) AT TIME ZONE 'UTC'
    AND 
    evt_block_time < FROM_UNIXTIME(1644944444 + 31536000) AT TIME ZONE 'UTC'
), 


balance_diff AS (
  SELECT 
    evt_block_number
    ,user
    ,MIN(evt_block_time) AS evt_block_time
    ,SUM(value) AS delta
  FROM (
    SELECT * FROM inflow
    UNION ALL
    SELECT * FROM outflow
  )
  WHERE user != 0x0000000000000000000000000000000000000000
  GROUP BY 1, 2
),

lead_balance_diff AS (
SELECT 
    *
    ,COALESCE(
        LEAD(evt_block_time) OVER (PARTITION BY user ORDER BY evt_block_number)
        ,FROM_UNIXTIME(1644944444 + 31536000) AT TIME ZONE 'UTC') AS evt_block_time_lead
    ,LEAD(evt_block_number) OVER (PARTITION BY user ORDER BY evt_block_number) AS evt_block_number_lead
FROM balance_diff
),

balance AS (
SELECT 
    evt_block_time
    ,user
    ,SUM(delta) OVER (PARTITION BY USER ORDER BY evt_block_number) AS amount
    ,date_diff('second', evt_block_time, evt_block_time_lead) AS delta_seconds
FROM lead_balance_diff
),

final AS (
    SELECT 
        user 
        ,(CAST(SUM(amount * delta_seconds) AS DOUBLE)/31536000)/1e18 AS avg_balance
    FROM
        balance
    GROUP BY 1
)

SELECT * FROM final
WHERE avg_balance != 0
AND 
--Gnosis DAO, and curve
user NOT IN (0x458cd345b4c05e8df39d0a07220feb4ec19f5e6f,0xbdf4488dcf7165788d438b62b4c8a333879b7078,0x2686d5E477d1AaA58BF8cE598fA95d97985c7Fb1)
ORDER BY 2 DESC
```