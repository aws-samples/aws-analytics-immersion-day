### 데이터베이스 생성

```text
CREATE DATABASE mydatabase;
```

### json 데이터 포맷으로 저장된 테이블 생성
```text
CREATE EXTERNAL TABLE IF NOT EXISTS mydatabase.retail_trans_json (
  `Invoice` string,
  `StockCode` string,
  `Description` string,
  `Quantity` int,
  `InvoiceDate` timestamp,
  `Price` float,
  `Customer_ID` string,
  `Country` string 
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES (
  'serialization.format' = '1'
) LOCATION 's3://aws-analytics-immersion-day-xxxxxxxx/json-data/'
TBLPROPERTIES ('has_encrypted_data'='false');
```

### Monthly Revenue 계산 쿼리
```text
SELECT date_trunc('month', invoicedate) invoice_year_month, sum(price*quantity) revenue
FROM mydatabase.retail_trans_json
WHERE invoicedate
    BETWEEN timestamp '2010-01-01'
        AND timestamp '2010-12-31'
GROUP BY date_trunc('month', invoicedate);


SELECT date_trunc('month', invoicedate) invoice_year_month, sum(price*quantity) revenue
FROM mydatabase.retail_parquet_ctas_table
WHERE invoicedate
    BETWEEN timestamp '2010-01-01'
        AND timestamp '2010-12-31'
GROUP BY date_trunc('month', invoicedate);


SELECT date_trunc('month', invoicedate) invoice_year_month, sum(price*quantity) revenue
FROM mydatabase.retail_parquet_snappy_ctas_table
WHERE invoicedate
    BETWEEN timestamp '2010-01-01'
        AND timestamp '2010-12-31'
GROUP BY date_trunc('month', invoicedate);
```

### CTAS 예제
```text
-- Parquet 데이터로 새 테이블을 생성
CREATE TABLE retail_parquet_ctas_table
WITH (
      external_location = 's3://aws-analytics-immersion-day-xxxxxxxx/parquet-data/',
      format = 'PARQUET')
AS SELECT * 
FROM retail_trans_json;


-- 데이터를 Snappy로 압축해서 Parquet 데이터로 새 테이블을 생성
CREATE TABLE retail_parquet_snappy_ctas_table
WITH (
      external_location = 's3://aws-analytics-immersion-day-xxxxxxxx/parquet-snappy-data/',
      format = 'PARQUET',
      parquet_compression = 'SNAPPY')
AS SELECT * 
FROM retail_trans_json;
```

### Reference
- https://docs.aws.amazon.com/ko_kr/athena/latest/ug/ctas-examples.html#ctas-example-format
- https://docs.aws.amazon.com/ko_kr/athena/latest/ug/ctas-examples.html#ctas-example-compression
