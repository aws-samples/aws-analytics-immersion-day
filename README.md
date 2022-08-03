# <a name="top"></a>AWS Analytics Immersion Day Workshop

이 실습의 목적은 Businesss Intelligence System을 aws의 analytics 서비스를 활용해서 구현해 보는 것 입니다.
이 실습을 통해서 `데이터 수집 -> 저장 -> 분석/처리 -> 시각화` 단계를 aws의 analytics 서비스를 이용해서
어떻게 구축할 수 있는지 경험할 수 있습니다.

* Read this in other languages: [English](README.en.md), [한국어](README.ko.md)

## Table of Contents
* [Solutions Architecture Overview](#solutions-architecture-overview)
* [사전 준비 작업](#preliminaries)
* [\[Step-1a\] 입력 데이터를 수신할 Kinesis Data Streams 생성하기](#kinesis-data-streams)
* [\[Step-1b\] 데이터를 S3에 저장하기 위한 Kinesis Data Firehose 생성하기](#kinesis-data-firehose)
* [\[Step-1c\] 데이터 파이프라인 동작 확인 하기](#kinesis-data-pipeline)
* [\[Step-1d\] Athena를 이용해서 데이터 분석 하기](#athena)
* [\[Step-1e\] QuickSight를 이용한 데이터 시각화](#amazon-quicksight-visualization)
* [(Optional)\[Step-1f\] AWS Lambda Function을 이용해서 S3에 저장된 작은 파일들을 큰 파일로 합치기](#athena-ctas-lambda-function)
* [\[Step-2a\] 실시간 데이터 분석을 위한 Amazon Elasticsearch Service 생성하기](#amazon-es)
* [\[Step-2b\] AWS Lambda Function을 이용해서 실시간 데이터를 ElasticSearch에 수집하기](#amazon-lambda-function)
* [\[Step-2c\] Kibana를 이용한 데이터 시각화](#amazon-es-kibana-visualization)
* [Recap and Review](#recap-and-review)
* [Resources](#resources)
* [Reference](#reference)
* [Appendix](#appendix)

## <a name="solutions-architecture-overview"></a>Solutions Architecture Overview
![aws-analytics-system-architecture](aws-analytics-system-arch.svg)

\[[Top](#Top)\]

## <a name="preliminaries"></a>사전 준비 작업
실습을 시작 하기 전에 필요한 IAM User, EC2를 생성하고 및 구성합니다.
 - [실습 환경 준비 하기](./doc_sources/prerequisites.md)
 
\[[Top](#Top)\]

## <a name="kinesis-data-streams"></a>입력 데이터를 수신할 Kinesis Data Streams 생성하기

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

AWS Management Console에서 Kinesis 서비스를 선택합니다.
1. **Get Started** 버튼을 클릭합니다.
2. **\[Create data stream\]** 버튼을 클릭합니다.
3. Kinesis stream name 에 원하는 이름(예: `retail-trans`)을 입력합니다.
4. Number of shards 에 원하는 shards 수(예: `1`)를 입력합니다.
5. **\[Create data stream\]** 버튼을 클릭 후, 생성된 kinesis stream의 status가 active가 될 때까지 기다립니다.

\[[Top](#top)\]

## <a name="kinesis-data-firehose"></a>데이터를 S3에 저장하기 위한 Kinesis Data Firehose 생성하기
Kinesis Data Firehose를 이용해서 실시간으로 데이터를 S3, Redshift, ElasticSearch 등의 목적지에 수집할 수 있습니다.
AWS Management Console에서 Kinesis 서비스를 선택합니다.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. **Get Started** 버튼을 클릭합니다.
2. Deliver streaming data with Kinesis Firehose delivery streams 메뉴의 **\[Create delivery stream\]** 을 클릭하여
새로운 Firehose 전송 스트림 생성을 시작합니다.
3. (Step 1: Name and source) Delivery stream name에 원하는 이름(예: `retail-trans`)를 입력합니다.
4. **Choose a source** 에서 `Kinesis Data Stream` 를 선택하고, 앞서 생성한 Kinesis Data Stream(예: `retail-trans`)을 선택 한 후,
**Next**를 클릭합니다.
5. (Step 2: Process records) **Transform source records with AWS Lambda / Convert record format** 은 
둘다 default 옵션 `Disabled`를 선택하고 **Next**를 클릭합니다.
6. (Step 3: Choose a destination) Destination은 Amazon S3를 선택하고, `Create new` 를 클릭해서 S3 bucket을 생성합니다.
S3 bucket 이름은 이번 실습에서는 `aws-analytics-immersion-day-xxxxxxxx` 형식으로 `xxxxxxxx` 는 bucket 이름이 겹치지 않도록 임의의 숫자나
문자를 입력 합니다.

    S3 prefix를 입력합니다. 예를 들어서 다음과 같이 입력 합니다.
    
    ```buildoutcfg
    json-data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/
    ```

    S3 error prefix를 입력합니다. 예를 들어서 다음과 같이 입력 합니다.
    ```buildoutcfg
    error-json/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/!{firehose:error-output-type}
    ```

    :warning: **S3 prefix 또는 S3 error prefix 패턴에는 줄 바꿈(`\n`) 문자가 없어야합니다. 예제 패턴을 복사하여 S3 prefix 또는 S3 error prefix에 붙여 넣었다면, 후행 줄 바꿈을 제거하는 것이 좋습니다.**

    S3 prefix와 3 error prefix 입력을 완료한 후에, Next를 클릭합니다.
    (참고: [Amazon S3 객체에 대한 사용자 지정 접두사](https://docs.aws.amazon.com/firehose/latest/dev/s3-prefixes.html))
7. (Step 4: Configure settings) S3 buffer conditions에서 Buffer size는 `1MB`, Buffer interval은 `60` seconds로 설정합니다.
8. 아래 IAM role에서 `Create or update IAM Role ...` 을 선택한 후, **\[Next\]** 버튼을 클릭합니다.
 ![aws-kinesis-firehose-create_new_iam_role](./assets/aws-kinesis-firehose-create_new_iam_role.png)
9. (Step 5: Review) Review에서 입력한 정보를 확인한 뒤 틀린 부분이 없다면, **\[Create delivery stream\]** 버튼을 클릭하여 Firehose 생성을 완료합니다.

\[[Top](#top)\]

## <a name="kinesis-data-pipeline"></a>데이터 파이프라인 동작 확인 하기
샘플 데이터를 이용해서 `Kinesis Data Streams -> Kinesis Data Firehose -> S3` 로 데이터가 정상적으로 수집되는지 확인합니다.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. 앞서 생성한 E2 인스턴스에 SSH 접속을 합니다.
2. `gen_kinesis_data.py`을 실행합니다.
    ```shell script
    $ python3 gen_kinesis_data.py --help
    usage: gen_kinesis_data.py [-h]
               [--region-name REGION_NAME]
               -I INPUT_FILE
               [--out-format {csv,tsv,json}]
               [--service-name {kinesis,firehose}]
               [--stream-name STREAM_NAME]
               [--max-count MAX_COUNT]
               [--dry-run]

    optional arguments:
      -h, --help            show this help message and exit
      --region-name REGION_NAME
                            aws region name (default: us-east-1)
      -I INPUT_FILE, --input-file INPUT_FILE
                            The input file path ex)
                            ./resources/online_retail.csv
      --out-format {csv,tsv,json}
      --service-name {kinesis,firehose}
      --stream-name STREAM_NAME
                            The name of the stream to put the data record into.
      --max-count MAX_COUNT
                            The max number of records to put.
      --dry-run
    
    $ python3 gen_kinesis_data.py -I resources/online_retail.csv \
    --region-name us-west-2 \
    --service-name kinesis \
    --out-format json \
    --stream-name retail-trans
    ```
3. 매 초 데이터가 발생하는 것을 확인합니다. 충분한 데이터 수집을 위해 실행 중인 상태로 다음 단계를 진행합니다.
4. 몇 분 뒤 생성한 S3 bucket을 확인해 보면, 생성된 원본 데이터가 Kinesis Data Firehose를 통해 S3에 저장되는 것을 확인할 수 있습니다. 

\[[Top](#top)\]

## <a name="athena"></a>Athena를 이용해서 데이터 분석 하기
Amazon Athena를 이용해서 S3에 저장된 데이터를 기반으로 테이블을 만들고, 테이블을 쿼리한 다음 쿼리 결과를 확인할 수 있습니다.
먼저 데이터를 쿼리하기 위해서 데이터베이스를 생성합니다.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

### 1단계: 데이터베이스 생성
1. Athena 콘솔을 엽니다.
2. Athena 콘솔을 처음 방문하면 시작하기 페이지로 이동합니다. **\[Get Started\]** 를 선택해 쿼리 편집기를 엽니다.
3. 처음 방문 하는 경우라면, **set up a query result location in Amazon S3** 를 클릭해서 Athena의 쿼리 결과를 저장할 s3 위치를 설정합니다.
 ![aws-athena-setup-query-results-location-01](./assets/aws-athena-setup-query-results-location-01.png)
이번 실습에서는 Kinesis Data Firehose 설정 단계에서 생성한 s3 bucket에 Athena의 쿼리 결과를 저장할 디렉터리를 생성합니다.
예를 들어, `s3://aws-analytics-immersion-day-xxxxxxxx/athena-query-results/` (`xxxxxxxx` 는 bucket 이름이 겹치지 않도록 입력한 임의의 숫자나
문자열 입니다.)
 ![aws-athena-setup-query-results-location-02](./assets/aws-athena-setup-query-results-location-02.png)
처음 방문하는 경우가 아니라면, Athena 쿼리 편집기가 열립니다.
4. Athena 쿼리 편집기에서 예제 쿼리가 있는 쿼리 창을 볼 수 있습니다. 쿼리 창의 아무 곳에나 쿼리를 입력하기 시작합니다.
5. `mydatabase` 라는 데이터베이스를 생성하려면 다음 CREATE DATABASE 문을 입력한 다음, **\[Run Query\]** 를 선택합니다.
    ```buildoutcfg
    CREATE DATABASE mydatabase
    ```
6. 카탈로그 디스플레이가 새로 고쳐지고 왼쪽 **\[Catalog\]** 대시보드의 **\[DATABASE\]** 목록에 `mydatabase`가 표시되는지 확인합니다.
 ![aws-athena-create-database](./assets/aws-athena-create-database.png)

### 2단계: 테이블 생성
1. **\[DATABASE\]** 에 `mydatabase`가 선택되었는지 확인한 후 **\[New Query\]** 를 선택합니다.
2. 쿼리 창에 다음 CREATE TABLE 문을 입력한 후 **\[Run Query\]** 를 선택합니다.
    ```buildoutcfg
    CREATE EXTERNAL TABLE `mydatabase.retail_trans_json`(
      `invoice` string COMMENT 'Invoice number', 
      `stockcode` string COMMENT 'Product (item) code', 
      `description` string COMMENT 'Product (item) name', 
      `quantity` int COMMENT 'The quantities of each product (item) per transaction', 
      `invoicedate` timestamp COMMENT 'Invoice date and time', 
      `price` float COMMENT 'Unit price', 
      `customer_id` string COMMENT 'Customer number', 
      `country` string COMMENT 'Country name')
    PARTITIONED BY ( 
      `year` int, 
      `month` int, 
      `day` int, 
      `hour` int)
    ROW FORMAT SERDE 
      'org.openx.data.jsonserde.JsonSerDe' 
    STORED AS INPUTFORMAT 
      'org.apache.hadoop.mapred.TextInputFormat' 
    OUTPUTFORMAT 
      'org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat'
    LOCATION
      's3://aws-analytics-immersion-day-xxxxxxxx/json-data'
    ```
    테이블 `retail_trans_json`가 생성되고 데이터베이스의 **\[Catalog\]** 대시보드에 표시됩니다.
3. 테이블을 생성한 이후 **\[New Query\]** 를 선택하고 다음을 실행해서, 파티션의 데이터를 로드합니다.
    ```buildoutcfg
    MSCK REPAIR TABLE mydatabase.retail_trans_json
    ```

### 3단계: 데이터 쿼리
+ **\[New Query\]** 를 선택하고 쿼리 창의 아무 곳에나 다음 문을 입력한 다음 **\[Run Query\]** 를 선택합니다.
    ```buildoutcfg
    SELECT *
    FROM retail_trans_json
    LIMIT 10
    ```
    다음과 같은 형식의 결과가 반환됩니다.
    ![aws_athena_select_all_limit_10](./assets/aws_athena_select_all_limit_10.png)

\[[Top](#top)\]

## <a name="amazon-quicksight-visualization"></a>QuickSight를 이용한 데이터 시각화
이번에는 Amazon QuickSight를 통해 데이터 시각화 작업을 합니다.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. [QuickSight 콘솔](https://quicksight.aws.amazon.com)로 이동합니다.
2. QuickSight에 가입하기 위해 **\[Sign up for QuickSight\]** 버튼을 클릭합니다.
3. Standard Edition을 선택한 후 **\[Continue\]** 버튼을 클릭합니다.
4. QuickSight account name은 임의로 지정(중복될 경우 계정이 생성되지 않습니다) 하고,
Notification email address는 개인 Email 주소를 입력합니다.
5. QuckSight가 S3에 Access해야 하므로, **\[Choose S3 buckets\]** 를 클릭합니다.
 ![aws-quicksight-access-s3](./assets/aws-quicksight-access-s3.png)
6. 아래와 같은 창이 뜨면, 데이터가 저장되어 있는 `aws-analytics-immersion-day-xxxxxxxx` 를 선택한 후 **\[Finish\]** 를 클릭합니다.
 ![aws-quicksight-choose-s3-bucket](./assets/aws-quicksight-choose-s3-bucket.png)
7. 계정이 생성된 후 **\[Go to Amazon QuickSight\]** 버튼을 클릭합니다.
8. 우측 상단에 region이 데이터를 저장하고 있는 S3 bucket의 region과 동일하게 설정한 후, 
좌측 상단 **\[New Analysis\]** 를 클릭합니다.
9. **\[New Data Set\]** 버튼을 클릭합니다.
 ![aws-quicksight-new_data_sets](./assets/aws-quicksight-new_data_sets.png)
10. `Athena` 를 클릭하고 팝업 창의 Data source name에 `retail-quicksight` 를 입력(임의의 값 입력 가능)하고,
**\[Validate connection\]** 을 클릭 해서 `Validated` 상태로 변경되면, **\[Create data source\]** 버튼을 클릭합니다.
 ![aws-quicksight-athena_data_source](./assets/aws-quicksight-athena_data_source.png)
11. Choose your table 화면에서 Database는 `mydatabase` (앞서 생성한 Athena 데이터베이스),
Tables 에서 `retail_trans_json` 를 선택하고 Select 버튼을 클릭합니다.
 ![aws-quicksight-athena-choose_your_table](./assets/aws-quicksight-athena-choose_your_table.png)
12. Finish data set creation 화면에서 **\[Visualize\]** 버튼을 클릭 합니다.
`retail_trans_json` 테이블 데이터가 QuickSight SPICE 엔진에 로딩 되었는지 확인합니다.
13. `InvoicdDate` 별 `Quantity`, `Price`를 시각화 해 보겠습니다. 좌측 Fields list에서 `invoicedate`, `price`, `quantity` field를 차례대로 선택합니다.
Visual types는 세로 막대 그래프를 선택합니다.
 ![aws-quicksight-bar-chart](./assets/aws-quicksight-bar-chart.png)
14. 방금 만든 Dashboard를 다른 사용자에게 공유해 보겠습니다. 좌측 상단 유저 아이콘을 클릭하고 \[Manage QuickSight\] 를 클릭합니다.
15. Invite users 버튼을 클릭한 후 임의의 사용자 계정명(BI_user01)을 입력한 후 우측 **\[+\]** 버튼을 클릭합니다.
Email은 다른 사용자의 Email 주소를 입력하고 Role은 AUTHOR, IAM User는 NO를 선택한 후 Invite 버튼을 클릭합니다.
 ![aws-quicksight-user-invitation](./assets/aws-quicksight-user-invitation.png)
16. 사용자는 다음과 같은 Invitation Email을 받고 Click to accept invitation을 클릭하면 계정 생성 메뉴에서 비밀번호를 변경할 수 있습니다.
 ![aws-quicksight-user-email](./assets/aws-quicksight-user-email.png)
17. QuickSight 화면으로 돌아가서 우측 상단의 **Share > Share analysis** 를 클릭합니다.
 ![aws-quicksight-share-analysis.png](./assets/aws-quicksight-share-analysis.png)
18. BI_user01을 선택한 후 Share 버튼을 클릭합니다.
 ![aws-quicksight-share-analysis-users](./assets/aws-quicksight-share-analysis-users.png)
19. 사용자는 다음과 같은 Email을 수신합니다. **\[Click to View\]** 를 클릭하여 분석결과를 확인할 수 있습니다.
 ![aws-quicksight-user-email-click-to-view](./assets/aws-quicksight-user-email-click-to-view.png)

\[[Top](#top)\]

## <a name="athena-ctas-lambda-function"></a>(Optional) AWS Lambda Function을 이용해서 S3에 저장된 작은 파일들을 큰 파일로 합치기
실시간으로 들어오는 데이터를 Kinesis Data Firehose를 이용해서 S3에 저장할 경우, 데이터 사이즈가 작은 파일들이 생성됩니다.
Amazon Athena의 쿼리 성능 향상을 위해서 작은 파일들을 하나의 큰 파일로 합쳐주는 것이 좋습니다. 이러한 작업을 주기적으로 실행하기 위해서
Athena의 CTAS(Create Table As Select) 쿼리를 실행하는 AWS Lambda function 함수를 생성하고자 합니다.

![aws-analytics-system-build-steps-extra](./assets/aws-analytics-system-build-steps-extra.svg)

### 1단계: CTAS 쿼리 결과를 저장하는 테이블 생성하기
1. Athena 콘솔에 접속해서 Athena 쿼리 편집기로 이동합니다.
2. **\[DATABASE\]** 에서 mydatabase를 선택하고, **\[New Query\]** 를 선택합니다.
3. 쿼리 창에 다음 CREATE TABLE 문을 입력한 후 **\[Run Query\]** 를 선택합니다.<br/>
이번 실습에서는 `retal_tran_json` 테이블의 json 포맷 데이터를 parquet 포맷으로 변경해서 `ctas_retail_trans_parquet` 이라는 테이블에 저장할 것 입니다.<br/>
`ctas_retail_trans_parquet` 테이블의 데이터는 앞서 생성한 S3 bucket의 `s3://aws-analytics-immersion-day-xxxxxxxx/parquet-retail-trans` 위치에 저장할 것 입니다.
    ```buildoutcfg
    CREATE EXTERNAL TABLE `mydatabase.ctas_retail_trans_parquet`(
      `invoice` string COMMENT 'Invoice number', 
      `stockcode` string COMMENT 'Product (item) code', 
      `description` string COMMENT 'Product (item) name', 
      `quantity` int COMMENT 'The quantities of each product (item) per transaction', 
      `invoicedate` timestamp COMMENT 'Invoice date and time', 
      `price` float COMMENT 'Unit price', 
      `customer_id` string COMMENT 'Customer number', 
      `country` string COMMENT 'Country name')
    PARTITIONED BY ( 
      `year` int, 
      `month` int, 
      `day` int, 
      `hour` int)
    ROW FORMAT SERDE 
      'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
    STORED AS INPUTFORMAT 
      'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
    OUTPUTFORMAT 
      'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
    LOCATION
      's3://aws-analytics-immersion-day-xxxxxxxx/parquet-retail-trans'
    TBLPROPERTIES (
      'has_encrypted_data'='false', 
      'parquet.compression'='SNAPPY')
    ;
    ```

### 2단계: AWS Lambda 함수 생성하기
1. **AWS Lambda 콘솔** 을 엽니다.
2. **\[Create a function\]** 을 선택합니다.
3. Function name(함수 이름)에 `MergeSmallFiles` 을 입력합니다.
4. Runtime 에서 `Python 3.8` 을 선택합니다.
5. **\[Create a function\]** 을 선택합니다.
 ![aws-athena-ctas-lambda-create-function](./assets/aws-athena-ctas-lambda-create-function.png)
6. Designer 탭에 **\[Add trigger\]** 를 선택합니다.
7. **Trigger configuration** 의 `Select a trigger` 에서 **CloudWatch Events/EventBridge** 를 선택 합니다.
Rule에서 `Create a new rule` 선택하고, Rule name에 적절한 rule name(예: `MergeSmallFilesEvent`)을 입력 합니다.
Rule type으로 `Schedule expression`을 선택하고, Schedule expression에 매시각 5분 마다 작업이 실행되도록,
`cron(5 * * * *)` 입력합니다.
 ![aws-athena-ctas-lambda-add-trigger](./assets/aws-athena-ctas-lambda-add-trigger.png)
8. **Trigger configuration** 에서 **\[Add\]** 를 클릭합니다.
9. Function code의 코드 편집기에 `athena_ctas.py` 파일의 코드를 복사해서 붙여넣은 후, **Deploy** 버튼을 클릭합니다.
10. **\[Add environment variables\]** 를 클릭해서 다음 Environment variables을 등록합니다.
    ```shell script
    OLD_DATABASE=<source database>
    OLD_TABLE_NAME=<source table>
    NEW_DATABASE=<destination database>
    NEW_TABLE_NAME=<destination table>
    WORK_GROUP=<athena workgroup>
    OLD_TABLE_LOCATION_PREFIX=<s3 location prefix of source table>
    OUTPUT_PREFIX=<destination s3 prefix>
    STAGING_OUTPUT_PREFIX=<staging s3 prefix used by athena>
    COLUMN_NAMES=<columns of source table excluding partition keys>
    ```
    예를 들어, 다음과 같이 Environment variables을 설정합니다.
    ```buildoutcfg
    OLD_DATABASE=mydatabase
    OLD_TABLE_NAME=retail_trans_json
    NEW_DATABASE=mydatabase
    NEW_TABLE_NAME=ctas_retail_trans_parquet
    WORK_GROUP=primary
    OLD_TABLE_LOCATION_PREFIX=s3://aws-analytics-immersion-day-xxxxxxxx/json-data
    OUTPUT_PREFIX=s3://aws-analytics-immersion-day-xxxxxxxx/parquet-retail-trans
    STAGING_OUTPUT_PREFIX=s3://aws-analytics-immersion-day-xxxxxxxx/tmp
    COLUMN_NAMES=invoice,stockcode,description,quantity,invoicedate,price,customer_id,country
    ```
11. Athena 쿼리를 수행하는데 필요한 IAM Policy를 추가하기 위해서 Execution role에서 
`View the MergeSmallFiles-role-XXXXXXXX role on the IAM console.` 을 클릭 해서 IAM Role을 수정합니다.
 ![aws-athena-ctas-lambda-execution-iam-role](./assets/aws-athena-ctas-lambda-execution-iam-role.png)
12. IAM Role의 **\[Permissions\]** 탭에서 **\[Attach policies\]** 버튼을 클릭 후, 
**AmazonAthenaFullAccess**, **AmazonS3FullAccess** 를 차례로 추가 합니다.
 ![aws-athena-ctas-lambda-iam-role-policies](./assets/aws-athena-ctas-lambda-iam-role-policies.png)
13. Basic settings에서 **\[Edit\]** 선택합니다. Memory와 Timeout을 알맞게 조정합니다.
이 실습에서는 Timout을 `5 min` 으로 설정합니다.

\[[Top](#top)\]

## <a name="amazon-es"></a>실시간 데이터 분석을 위한 Amazon Elasticsearch Service 생성하기
실시간으로 데이터를 저장하고, 분석하기 위해서 Elasticsearch cluster를 생성합니다.
Amazon ES 도메인은 Elasticsearch 클러스터와 동의어입니다. 도메인은 설정, 인스턴스 유형, 인스턴스 수, 스토리지 리소스를 지정한 설정입니다.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. AWS Management Console에서 Analytics의 **Elasticsearch** 서비스를 선택합니다.
2. (Step 1: Choose deployment type) **Create a new domain(새 도메인 생성)** 을 선택합니다.
3. **Elasticsearch 도메인 생성** 페이지에서 **Deployment type(배포 유형)** 에 대해 **Production(프로덕션)** 을 선택합니다.
 ![amazon-es-deployment-type](./assets/amazon-es-deployment-type.png)
4. **버전**에서 해당 도메인의 Elasticsearch 버전을 선택합니다. 지원되는 최신 버전을 선택하는 것이 좋습니다. 자세한 내용은 [지원되는 Elasticsearch 버전](https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/what-is-amazon-elasticsearch-service.html#aes-choosing-version) 단원을 참조하십시오.
5. **\[Next\]** 를 선택합니다.
6. (Step 2: Configure domain) 도메인의 이름을 입력합니다. 이 실습에서는 이후에 다룰 `retail`를 예제 도메인 이름으로 사용합니다.
7. **인스턴스 유형** 에서 Amazon ES 도메인의 인스턴스 유형을 선택합니다. 이 실습에서는 테스트 목적에 적합한 소용량의 경제적인 인스턴스 유형
`t2.medium.elasticsearch`를 사용하는 것이 좋습니다.
8. **인스턴스 수** 에 원하는 인스턴스 수를 입력합니다. 이 실습에서는 기본값 `3`을 사용합니다.
9. 스토리지 유형에서 EBS를 선택합니다.
    + a. EBS volume type(EBS 볼륨 유형)에 일반용(SSD)을 선택합니다. 자세한 내용은 Amazon EBS 볼륨 유형을 참조하십시오.
    + b. EBS volume size(EBS 볼륨 크기)에 각 데이터 노드용 외부 스토리지의 크기를 GiB 단위로 입력합니다. 이 실습에서는 기본값 `10`을 사용합니다.
    ![amazon-es-config-domain](./assets/amazon-es-config-domain.png)
10. 지금은 **Dedicated master nodes(전용 마스터 노드), Snapshot configuration(스냅샷 구성)** 및 **Optional Elasticsearch cluster settings(선택적 Elasticsearch 클러스터 설정)** 섹션을 무시할 수 있습니다.
11. **\[Next\]** 를 선택합니다.
12. (Step 3: Configure access and security) **Network configuration(네트워크 구성)** 의 경우 **VPC access** 를 선택합니다.
적절한 VPC와 subnet을 선택합니다. Security Groups으로 준비 단계에서 생성한 `es-cluster-sg`를 선택합니다.
13. 지금은 **Amazon Cognito Authentication(Amazon Cognito 인증)** 과 **Fine–grained access control** 을 disable 합니다.
 ![amazon-es-access-control](./assets/amazon-es-access-control.png)
14. **Access policy(액세스 정책)** 의 경우 **Domain access policy(도메인 액세스 정책)** 에서 **JSON defined access policy(JSON 정의 액세스 정책)** 선택한 다음,
**Add or edit the access policy(액세스 정책 추가 또는 편집)** 에 다음 템플릿을 이용해서 **JSON defined access policy** 를 생성해서 입력 합니다.
    + JSON defined access policy Template - `<DOMAIN-NAME>` 에 **(Step 2: Configure domain)** 에서 입력한 도메인 이름을 일력합니다.
        ```json
        {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Principal": {
                "AWS": "*"
              },
              "Action": [
                "es:Describe*",
                "es:List*",
                "es:Get*",
                "es:ESHttp*"
              ],
              "Resource": "arn:aws:es:<region-id>:<account-id>:domain/<DOMAIN-NAME>/*"
            }
          ]
        }
        ```
    + 예) 이번 실습에서는 `retail` 을 도메인 이름으로 사용했기 때문에, 아래와 같이 JSON defined access policy 를 생성합니다.
        ```json
        {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Principal": {
                "AWS": "*"
              },
              "Action": [
                "es:Describe*",
                "es:List*",
                "es:Get*",
                "es:ESHttp*"
              ],
              "Resource": "arn:aws:es:us-west-2:123456789012:domain/retail/*"
            }
          ]
        }
        ```
    + JSON defined access policy 생성을 완료하면, 아래와 같은 화면을 볼 수 있을 것입니다.
    ![amazon-es-json-access-policy](./assets/amazon-es-json-access-policy.png)
15. **Encryption(암호화)** 에서 **Require HTTPS for all traffic to the domain** 만 허용하고, 다른 항목은 disable 합니다.
 ![amazon-es-encryption-config](./assets/amazon-es-encryption-config.png)
16. **Encryption(암호화)** 의 모든 기본값을 유지합니다. **\[Next\]** 를 선택합니다.
17. **Review** 페이지에서 도메인 구성을 검토한 다음 **확인**을 선택합니다.

\[[Top](#top)\]

## <a name="amazon-lambda-function"></a>AWS Lambda Function을 이용해서 실시간 데이터를 ElasticSearch에 수집하기
Lambda function을 이용해서 Amazon ES에 데이터를 실시간으로 색인할 수 있습니다.
이번 실습에서는 AWS Lambda 콘솔을 사용하여 Lambda 함수를 생성합니다.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

### Lambda 함수에서 사용할 공통 라이브러를 Layers에 추가하려면,
1. **AWS Lambda 콘솔** 을 엽니다.
2. **Layers** 메뉴에 들어가서 **\[Create layer\]** 을 선택합니다.
3. Name에 `es-lib` 를 입력합니다.
4. `Upload a file from Amazon S3` 를 선택하고, 라이브러리 코드가 저장된 s3 link url 또는 압축한 라이브러리 코드 파일을 입력합니다.
`es-lib.zip` 생성 방법은 [AWS Lambda Layer에 등록할 Python 패키지 생성 예제](#aws-lambda-layer-python-packages) 를 참고하세요.
5. `Compatible runtimes` 에서 `Python 3.8` 을 선택합니다.
 ![aws-lambda-create-layer](./assets/aws-lambda-create-layer.png)

### Lambda 함수를 생성하려면,
1. **AWS Lambda 콘솔** 을 엽니다.
2. **\[Create a function\]** 을 선택합니다.
3. Function name(함수 이름)에 `UpsertToES` 을 입력합니다.
4. Runtime 에서 `Python 3.8` 을 선택합니다.
5. **\[Create a function\]** 을 선택합니다.
 ![aws-lambda-create-function](./assets/aws-lambda-create-function.png)
6. Designer(디자이너) 에서 layers를 선택합니다. Layers에서 Add a layer를 선택합니다.
7. Custom layers를 클릭하고 Name과 Version으로 앞서 생성한 layer의 Name과 Version을 선택합니다.
 ![aws-lambda-add-layer-to-function](./assets/aws-lambda-add-layer-to-function.png)
8. **\[Add\]** 클릭합니다.
9. Designer(디자이너) 에서 `UpsertToES` 을 선택하여 함수의 코드 및 구성으로 돌아갑니다.
10. Function code의 코드 편집기에 `upsert_to_es.py` 파일의 코드를 복사해서 붙여넣은 후, **Deploy** 버튼을 클릭합니다.
11. Environment variables 에서 **\[Edit\]** 를 클릭합니다.
12. **\[Add environment variables\]** 를 클릭해서 아래 4개의 Environment variables을 등록합니다.
    ```shell script
    ES_HOST=<elasticsearch service domain>
    ES_INDEX=<elasticsearch index name>
    ES_TYPE=<elasticsearch type name>
    REQUIRED_FIELDS=<primary key로 사용될 column 목록>
    REGION_NAME=<region-name>
    DATE_TYPE_FIELDS=<column 중, date 또는 timestamp 데이터 타입의 column>
    ```
    예를 들어, 다음과 같이 Environment variables을 설정합니다.
    ```buildoutcfg
    ES_HOST=vpc-retail-xkl5jpog76d5abzhg4kyfilymq.us-west-1.es.amazonaws.com
    ES_INDEX=retail
    ES_TYPE=trans
    REQUIRED_FIELDS=Invoice,StockCode,Customer_ID
    REGION_NAME=us-west-2
    DATE_TYPE_FIELDS=InvoiceDate
    ```
13. **\[Save\]** 선택합니다.
14. lambda 함수를 VPC 내에서 실행 하고, Kinesis Data Streams에서 데이터를 읽기 위해서,
lamba 함수 실행에 필요한 Execution role에 필요한 IAM Policy를 추가햐야 합니다.
IAM Role 수정을 위해서 `View the UpsertToES-role-XXXXXXXX role on the IAM console.` 을 클릭 합니다.
 ![aws-lambda-execution-iam-role](./assets/aws-lambda-execution-iam-role.png)
15. IAM Role의 **\[Permissions\]** 탭에서 **\[Attach policies\]** 버튼을 클릭 후, 
**AWSLambdaVPCAccessExecutionRole**, **AmazonKinesisReadOnlyAccess** 를 차례로 추가 합니다.
 ![aws-lambda-iam-role-policies](./assets/aws-lambda-iam-role-policies.png)
16. VPC 항목에서 **\[Edit\]** 버튼을 클릭해서 Edit VPC 화면으로 이동 한다. VPC connection 에서 `Custom VPC` 를 선택합니다.
Elasticsearch service의 도메인을 생성한 VPC와 subnets을 선택하고, Elasticsearch service 도메인에 접근이 허용된
security groups을 선택합니다.
17. Basic settings에서 **\[Edit\]** 선택합니다. Memory와 Timeout을 알맞게 조정합니다. 이 실습에서는 Timout을 `5 min` 으로 설정합니다.
18. 다시 Designer 탭으로 돌아가서 **\[Add trigger\]** 를 선택합니다.
19. **Trigger configuration** 의 `Select a trigger` 에서 **Kinesis** 를 선택 합니다.
20. Kinesis stream 에서 앞서 생성한 Kinesis Data Stream(`retail-trans`)을 선택합니다.
21. **\[Add\]** 를 선택합니다.
 ![aws-lambda-kinesis](./assets/aws-lambda-kinesis.png)

\[[Top](#top)\]

## <a name="amazon-es-kibana-visualization"></a>Kibana를 이용한 데이터 시각화
Amazon Elasticsearch Service에서 수집된 데이터를 Kibana를 이용해서 시각화 작업을 합니다.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. Amazon Elasticsearch Cluster를 VPC의 private subnet에 생성했기 때문에, Amazon Elasticsearch endpoint와 Kibana endpoint를 public 인터넷으로 접근할 수 없다. 따라서 Elasticsearch 에 접속하기 위해서 ssh tunnel을 생성하고, local port forwarding을 해야 한다.<br>
Mac 또는 Linux 사용자의 경우, 아래와 같이 개인 Local PC의 ssh config 파일에 ssh tunnel 설정을 추가 한다.
Windows 사용자의 경우, [여기](#SSH-Tunnel-with-PuTTy-on-Windows)를 참고한다.
    ```shell script
    # Elasticsearch Tunnel
    Host estunnel
      HostName <EC2 Public IP of Bastion Host>
      User ec2-user
      IdentitiesOnly yes
      IdentityFile ~/.ssh/analytics-hol.pem
      LocalForward 9200 <Elasticsearch Endpoint>:443
    ```
  + **EC2 Public IP of Bastion Host** 은 **실습 환경 구성** 단계에서 생성한 EC2 인스턴스의 Public IP 를 사용한다.
  + 예)
    ```shell script
    ~$ ls -1 .ssh/
    analytics-hol.pem
    config
    id_rsa
    ~$ tail .ssh/config
    # Elasticsearch Tunnel
    Host estunnel
      HostName 214.132.71.219
      User ubuntu
      IdentitiesOnly yes
      IdentityFile ~/.ssh/analytics-hol.pem
      LocalForward 9200 vpc-retail-qvwlxanar255vswqna37p2l2cy.us-west-2.es.amazonaws.com:443
    ~$
    ```
2. Terminal 에서 `ssh -N estunnel` 를 실행합니다.
3. Web browser에서 `https://localhost:9200/_plugin/kibana/` 으로 접속합니다.
4. (Home) Add Data to Kibana 에서 **\[Use Elasticsearch data / Connect to your Elasticsearch index\]** 클릭한다.
 ![kibana-01-add_data](./assets/kibana-01-add_data.png)
5. (Management / Create index pattern) Create index pattern의 **Step 1 of 2: Define index pattern** 에서
Index pattern에 `retail*` 을 입력합니다.
 ![kibana-02a-create-index-pattern](./assets/kibana-02a-create-index-pattern.png)
6. (Management / Create index pattern) **\[> Next step\]** 을 선택합니다.
7. (Management / Create index pattern) Create index pattern의 **Step 2 of 2: Configure settings** 에서
Time Filter field name에 `InvoiceDate` 를 선택합니다.
 ![kibana-02b-create-index-pattern-configure-settings](./assets/kibana-02b-create-index-pattern-configure-settings.png)
8. (Management / Create index pattern) **\[Create index pattern\]** 을 클릭합니다.
 ![kibana-02c-create-index-pattern-review](./assets/kibana-02c-create-index-pattern-review.png)
9. (Management / Advanced Settings) 왼쪽 사이드바 메뉴에서 **\[Advanced Settings\]** 를 선택한 후, **Timezone for date formatting**을 `Etc/UTC` 로 설정합니다. 테스트용 데이터의 로그 생성 시간이 `UTC` 기준이기 때문에 Kibana의 Timezone 역시 `UTC`로 설정합니다.
 ![kibana-02d-management-advanced-setting](./assets/kibana-02d-management-advanced-setting.png)
10. (Discover) Index pattern 생성을 완료 후, Discover를 선택해서 Elasticsearch 수집된 데이터를 확인합니다.
 ![kibana-03-discover](./assets/kibana-03-discover.png)
11. (Discover) `InvoicdDate` 별 `Quantity`를 시각화 해 보겠습니다. 좌측의 Available fields에서 invoicdDate를
선택하고, 하단에 있는 Visualize를 클릭합니다.
 ![kibana-04-discover-visualize](./assets/kibana-04-discover-visualize.png)
12. (Visualize) 아래와 같이 Data 탭의 Metrics에서 Y-Axis를 Aggregation은 `Sum`, Field는 `Quantity`를 선택 후 적용 합니다.
 ![kibana-05-discover-change-metrics](./assets/kibana-05-discover-change-metrics.png)
13. (Visualize) 좌측 상단의 **\[Save\]** 를 클릭하고, 저장한 그래프의 이름을 적은 후에 **\[Confirm Save\]** 를 클릭합니다.
 ![kibna-08-visualize-save](./assets/kibana-08-visualize-save.png)
14. (Dashboards) 좌측의 Dashboard 아이콘을 클릭 후, **\[Create new dashboard\]** 버튼을 클릭 합니다.
 ![kibana-09-dashboards](./assets/kibana-09-dashboards.png)
15. (Dashboards) 좌측 상단의 **\[Add\]** 를 클릭해서, **Add Panels** 에 이전 단계에서 생성한 그래프를 선택 합니다.
 ![kibana-10-import-visualization](./assets/kibana-10-import-visualization.png)
16. (Dashboards) 좌측 상단의 **\[Save\]** 를 클릭 한 후, Save dashboard에서 Title을 입력한 이후, **\[Confirm Save\]** 를 클릭 합니다.
![kibana-12-discover-save-dashboard](./assets/kibana-12-discover-save-dashboard.png)
17. (Dashboards) 아래와 같은 Dashboard를 확인할 수 있습니다.
 ![kibana-13-complete](./assets/kibana-13-complete.png)

\[[Top](#top)\]

## Recap and Review
이 실습을 통해서 데이터 파이프라인을 만들어서 실시간 데이터 처리와 배치 데이터 처리 layer로 구성된
Lambda Architecture 구조의 Business Intelligent System을 구축해 보셨습니다.

\[[Top](#top)\]

## Resources
+ slide: [AWS Analytics Immersion Day - Build BI System from Scratch](https://www.slideshare.net/ksmin23/aws-analytics-immersion-day-build-bi-system-from-scratch-230492367)
+ data source: [Online Retail II Data Set](https://archive.ics.uci.edu/ml/datasets/Online+Retail+II)

\[[Top](#Top)\]

## Reference
### AWS Developer Guide By Services
+ [Amazon Simple Storage Service (Amazon S3)](https://docs.aws.amazon.com/AmazonS3/latest/dev/Introduction.html)
+ [Amazon Athena](https://docs.aws.amazon.com/athena/latest/ug/what-is.html)
+ [Amazon Elasticsearch Service](https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/what-is-amazon-elasticsearch-service.html)
+ [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
+ [Amazon Kinesis Data Firehose](https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html)
+ [Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/introduction.html)
+ [Amazon QuickSight](https://docs.aws.amazon.com/quicksight/latest/user/welcome.html)
+ [AWS Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html#configuration-layers-path)
    + <a name="aws-lambda-layer-python-packages"></a>AWS Lambda Layer에 등록할 Python 패키지 생성 예제: **elasticsearch** 

      :warning: **Python 패키지를 생성할 때는 AWS Lambda의 실행환경과 동일한 환경에서 생성해야하므로, Amazon Linux에서 Python 패키지를 생성하는 것을 추천 드립니다.**
      <pre>
      [ec2-user@ip-172-31-6-207 ~] $ python3 -m venv es-lib # virtual environments을 생성함
      [ec2-user@ip-172-31-6-207 ~] $ cd es-lib
      [ec2-user@ip-172-31-6-207 ~] $ source bin/activate
      (es-lib) $ mkdir -p python_modules # 필요한 패키지를 저장할 디렉터리 생성
      (es-lib) $ pip install 'elasticsearch>=7.0.0,<7.11' requests requests-aws4auth -t python_modules # 필요한 패키지를 사용자가 지정한 패키지 디렉터리에 저장함
      (es-lib) $ mv python_modules python # 사용자가 지정한 패키지 디렉터리 이름을 python으로 변경함 (python 디렉터리에 패키지를 설치할 경우 에러가 나기 때문에 다른 이름의 디렉터리에 패키지를 설치 후, 디렉터리 이름을 변경함)
      (es-lib) $ zip -r es-lib.zip python/ # 필요한 패키지가 설치된 디렉터리를 압축함
      (es-lib) $ aws s3 mb s3://my-bucket-for-lambda-layer-packages # 압축한 패키지를 업로드할 s3 bucket을 생성함
      (es-lib) $ aws s3 cp es-lib.zip s3://my-bucket-for-lambda-layer-packages/var/ # 압축한 패키지를 s3에 업로드 한 후, lambda layer에 패키지를 등록할 때, s3 위치를 등록하면 됨
      (es-lib) $ deactivate
      </pre>
    + [How to create a Lambda layer using a simulated Lambda environment with Docker](https://aws.amazon.com/premiumsupport/knowledge-center/lambda-layer-simulated-docker/)
      ```
      $ cat <<EOF > requirements.txt
      > elasticsearch>=7.0.0,<7.11
      > requests==2.23.0
      > requests-aws4auth==0.9
      > EOF
      $ docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.7" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.7/site-packages/; exit"
      $ zip -r es-lib.zip python > /dev/null
      $ aws s3 mb s3://my-bucket-for-lambda-layer-packages
      $ aws s3 cp es-lib.zip s3://my-bucket-for-lambda-layer-packages/var/
      ```

### <a name="SSH-Tunnel-with-PuTTy-on-Windows"></a>SSH Tunnel for Kibana Instructions with PuTTy on Windows
+ [Windows SSH / Tunnel for Kibana Instructions - Amazon Elasticsearch Service](https://search-sa-log-solutions.s3-us-east-2.amazonaws.com/logstash/docs/Kibana_Proxy_SSH_Tunneling_Windows.pdf)
+ [Use an SSH Tunnel to access Kibana within an AWS VPC with PuTTy on Windows](https://amazonmsk-labs.workshop.aws/en/mskkdaflinklab/createesdashboard.html)

\[[Top](#top)\]

### Further readings
##### Amazon S3
+ [New – Automatic Cost Optimization for Amazon S3 via Intelligent Tiering](https://aws.amazon.com/ko/blogs/aws/new-automatic-cost-optimization-for-amazon-s3-via-intelligent-tiering/)

##### Amazon Athena
+ [Top 10 Performance Tuning Tips for Amazon Athena](https://aws.amazon.com/ko/blogs/big-data/top-10-performance-tuning-tips-for-amazon-athena/)
+ [Extract, Transform and Load data into S3 data lake using CTAS and INSERT INTO statements in Amazon Athena](https://aws.amazon.com/ko/blogs/big-data/extract-transform-and-load-data-into-s3-data-lake-using-ctas-and-insert-into-statements-in-amazon-athena/)
+ [Query Amazon S3 analytics data with Amazon Athena](https://aws.amazon.com/blogs/storage/query-amazon-s3-analytics-data-with-amazon-athena/)

##### Amazon Elasticsearch Service
+ [Elasticsearch tutorial: a quick start guide](https://aws.amazon.com/blogs/database/elasticsearch-tutorial-a-quick-start-guide/)
+ [Run a petabyte scale cluster in Amazon Elasticsearch Service](https://aws.amazon.com/blogs/database/run-a-petabyte-scale-cluster-in-amazon-elasticsearch-service/)
+ [Analyze user behavior using Amazon Elasticsearch Service, Amazon Kinesis Data Firehose and Kibana](https://aws.amazon.com/blogs/database/analyze-user-behavior-using-amazon-elasticsearch-service-amazon-kinesis-data-firehose-and-kibana/)

##### AWS Lambda
+ [Introduction to Messaging for Modern Cloud Architecture](https://aws.amazon.com/blogs/architecture/introduction-to-messaging-for-modern-cloud-architecture/)
+ [Understanding the Different Ways to Invoke Lambda Functions](https://aws.amazon.com/blogs/architecture/understanding-the-different-ways-to-invoke-lambda-functions/)

##### Amazon Kinesis Data Firehose
+ [Amazon Kinesis Data Firehose custom prefixes for Amazon S3 objects](https://aws.amazon.com/blogs/big-data/amazon-kinesis-data-firehose-custom-prefixes-for-amazon-s3-objects/)
+ [Amazon Kinesis Firehose Data Transformation with AWS Lambda](https://aws.amazon.com/blogs/compute/amazon-kinesis-firehose-data-transformation-with-aws-lambda/)

##### Amazon Kinesis Data Streams
+ [Under the hood: Scaling your Kinesis data streams](https://aws.amazon.com/blogs/big-data/under-the-hood-scaling-your-kinesis-data-streams/)
+ [Scale Amazon Kinesis Data Streams with AWS Application Auto Scaling](https://aws.amazon.com/blogs/big-data/scaling-amazon-kinesis-data-streams-with-aws-application-auto-scaling/)

##### Amazon Kinesis Data Analytics
+ [Streaming ETL with Apache Flink and Amazon Kinesis Data Analytics](https://aws.amazon.com/ko/blogs/big-data/streaming-etl-with-apache-flink-and-amazon-kinesis-data-analytics/)

##### Amazon QuickSight
+ [10 visualizations to try in Amazon QuickSight with sample data](https://aws.amazon.com/blogs/big-data/10-visualizations-to-try-in-amazon-quicksight-with-sample-data/)
+ [Visualize over 200 years of global climate data using Amazon Athena and Amazon QuickSight](https://aws.amazon.com/blogs/big-data/visualize-over-200-years-of-global-climate-data-using-amazon-athena-and-amazon-quicksight/)
+ [Advanced analytics with table calculations in Amazon QuickSight](https://aws.amazon.com/ko/blogs/big-data/advanced-analytics-with-table-calculations-in-amazon-quicksight/)

##### Etc
+ [Optimize downstream data processing with Amazon Kinesis Data Firehose and Amazon EMR running Apache Spark](https://aws.amazon.com/blogs/big-data/optimizing-downstream-data-processing-with-amazon-kinesis-data-firehose-and-amazon-emr-running-apache-spark/)
+ [Serverless Scaling for Ingesting, Aggregating, and Visualizing Apache Logs with Amazon Kinesis Firehose, AWS Lambda, and Amazon Elasticsearch Service](https://aws.amazon.com/blogs/database/serverless-scaling-for-ingesting-aggregating-and-visualizing-apache-logs-with-amazon-kinesis-firehose-aws-lambda-and-amazon-elasticsearch-service/)
+ [Analyze Apache Parquet optimized data using Amazon Kinesis Data Firehose, Amazon Athena, and Amazon Redshift](https://aws.amazon.com/blogs/big-data/analyzing-apache-parquet-optimized-data-using-amazon-kinesis-data-firehose-amazon-athena-and-amazon-redshift/)
+ [Our data lake story: How Woot.com built a serverless data lake on AWS](https://aws.amazon.com/blogs/big-data/our-data-lake-story-how-woot-com-built-a-serverless-data-lake-on-aws/)

##### Securely Connect Bastion Hosts
+ [Securing your bastion hosts with Amazon EC2 Instance Connect](https://aws.amazon.com/blogs/infrastructure-and-automation/securing-your-bastion-hosts-with-amazon-ec2-instance-connect/)

  ```
  $ # (1) Create a new ssh key.
  $ ssh-keygen -t rsa -f my_rsa_key

  $ # (2) Push your SSH public key to the instance.
  $ aws ec2-instance-connect send-ssh-public-key \
    --instance-id $BASTION_INSTANCE \
    --availability-zone $DEPLOY_AZ \
    --instance-os-user ec2-user \
    --ssh-public-key file:///path/to/my_rsa_key.pub

  $ # (3) Connect to the instance using your private key.
  $ ssh -i /path/to/my_rsa_key ec2-user@$BASTION_DNS_NAME
  ```

\[[Top](#top)\]

## Appendix

AWS CDK를 이용해서 배포하는 방법을 소개 합니다.

### Prerequisites
1. AWS CDK Toolkit을 설치합니다.

    ```shell script
    npm install -g aws-cdk
    ```

2. cdk가 정상적으로 설치되었는지, 다음 명령어를 실행해서 확인합니다.
    ```
    cdk --version
    ```
   예)
    ```shell script
    $ cdk --version
    2.10.0 (build e5b301f)
    ```

##### Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

\[[Top](#top)\]

### Deployment

CDK로 배포할 경우, 아래 아키텍처 그림의 `1(a), 1(b), 1(c), 1(f), 2(b), 2(a)`가 자동으로 생성됩니다.

![aws-analytics-system-build-steps-extra](./assets/aws-analytics-system-build-steps-extra.svg)

1. [Getting Started With the AWS CDK](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)를 참고해서 cdk를 설치하고,
cdk를 실행할 때 사용할 IAM User를 생성한 후, `~/.aws/config`에 등록합니다. ([사전 준비 작업](#preliminaries)를 참고해서 IAM User를 생성합니다.)
예를 들어서, cdk_user라는 IAM User를 생성 한 후, 아래와 같이 `~/.aws/config`에 추가로 등록합니다.

    ```shell script
    $ cat ~/.aws/config
    [profile cdk_user]
    aws_access_key_id=AKIAIOSFODNN7EXAMPLE
    aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    region=us-west-2
    ```

2. Lambda Layer에 등록할 Python 패키지를 생성해서 s3 bucket에 저장한다.
에를 들어, elasticsearch 패키지를 Lambda Layer에 등록 할 수 있도록 `lambda-layer-resources`라는 이름의 s3 bucket을 생성 후, 아래와 같이 저장합니다.

    ```shell script
    $ aws s3 ls s3://lambda-layer-resources/var/
    2019-10-25 08:38:50          0
    2019-10-25 08:40:28    1294387 es-lib.zip
    ```

3. 소스 코드를 git에서 다운로드 받은 후, `S3_BUCKET_LAMBDA_LAYER_LIB` 라는 환경 변수에 lambda layer에 등록할 패키지가 저장된 s3 bucket 이름을
설정 한 후, `cdk deploy` 명령어를 이용해서 배포합니다.

    ```shell script
    $ git clone https://github.com/aws-samples/aws-analytics-immersion-day.git
    $ cd aws-analytics-immersion-day
    $ python3 -m venv .env
    $ source .env/bin/activate
    (.env) $ pip install -r requirements.txt
    (.env) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    (.env) $ export CDK_DEFAULT_REGION=us-west-2
    (.env) $ cdk bootstrap aws://${CDK_DEFAULT_ACCOUNT}/${CDK_DEFAULT_REGION}
    (.env) $ export S3_BUCKET_LAMBDA_LAYER_LIB=lambda-layer-resources
    (.env) $ cdk --profile cdk_user deploy
    ```

   :white_check_mark: `cdk bootstrap ...` 명령어는 CDK toolkit stack 배포를 위해 최초 한번만 실행 하고, 이후에 배포할 때는 CDK toolkit stack 배포 없이 `cdk deploy` 명령어만 수행하면 됩니다.

    ```shell script
    (.env) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    (.env) $ export CDK_DEFAULT_REGION=us-west-2
    (.env) $ export S3_BUCKET_LAMBDA_LAYER_LIB=lambda-layer-resources
    (.env) $ cdk --profile cdk_user deploy
    ```

4. 배포한 애플리케이션을 삭제하려면, `cdk destroy` 명령어를 아래와 같이 실행 합니다.
    ```shell script
    (.env) $ cdk --profile cdk_user destroy
    ```

\[[Top](#top)\]

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
