# <a name="top"></a>AWS Analytics Immersion Day Workshop

The purpose of this lab is to implement a Businesss Intelligence(BI) System using AWS Analytics Services.<br/>
Through this lab, you will set up a `Data Collection -> Store -> Analysis/Processing -> Visualization` pipeline.

## Table of Contents
* [Solutions Architecture Overview](#solutions-architecture-overview)
* [Lab setup](#preliminaries)
* [\[Step-1a\] Create Kinesis Data Streams to receive input data](#kinesis-data-streams)
* [\[Step-1b\] Create Kinesis Data Firehose to store data in S3](#kinesis-data-firehose)
* [\[Step-1c\] Verify data pipeline operation](#kinesis-data-pipeline)
* [\[Step-1d\] Analyze data using Athena](#athena)
* [\[Step-1e\] Data visualization with QuickSight](#amazon-quicksight-visualization)
* [(Optional)\[Step-1f\] Combine small files stored in S3 into large files using AWS Lambda Function](#athena-ctas-lambda-function)
* [\[Step-2a\] Create Amazon Elasticsearch Service for Real-Time Data Analysis](#amazon-es)
* [\[Step-2b\] Ingest real-time data into ElasticSearch using AWS Lambda Functions](#amazon-lambda-function)
* [\[Step-2c\] Data visualization with Kibana](#amazon-es-kibana-visualization)
* [Recap and Review](#recap-and-review)
* [Resources](#resources)
* [Reference](#reference)
* [Appendix](#appendix)

## <a name="solutions-architecture-overview"></a>Solutions Architecture Overview
![aws-analytics-system-architecture](aws-analytics-system-arch.svg)

\[[Top](#Top)\]

## <a name="preliminaries"></a>Lab setup
Before starting the lab, create and configure EC2, the IAM user you need.
 - [Prepare the lab environment](./doc_sources/prerequisites.en.md)
 
\[[Top](#Top)\]

## <a name="kinesis-data-streams"></a>Create Kinesis Data Streams to receive input data

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

Select **Kinesis** from the list of services on the AWS Management Console.
1. Make sure the **Kinesis Data Streams** radio button is selected and click **Create data stream** button.
2. Enter `retail-trans` as the Data stream name.
3. Enter the desired name for **Kinesis stream name** (e.g. `retail-trans`).
4. Choose either the **On-demand** or **Provisioned** capacity mode.<br/>
   With the **On-demand mode**, you can then choose **Create Kinesis stream** to create your data stream.<br/>
   With the **Provisioned** mode, you must then specify the number of shards you need, and then choose **Create Kinesis stream**.<br/>
   If you choose **Provisioned** mode, enter `1` in **Number of open shards** under **Data stream capacity**.
5. Click the **Create data stream** button and wait for the status of the created kinesis stream to become active.

\[[Top](#top)\]

## <a name="kinesis-data-firehose"></a>Create Kinesis Data Firehose to store data in S3
Kinesis Data Firehose will allow collecting data in real-time and batch it to load into a storage location such as Amazon S3, Amazon Redshift or ElasticSearch.<br/>

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. If you are on the Kinesis Data Stream page from the previous step, select **Delivery streams** from the left sidebar. If you are starting from the Kinesis landing page, select the **Kinesis Data Firehose** radio button and click the **Create delivery stream** button.
2. (Step 1: Name and source) For **Delivery stream name** enter `retail-trans`.
3. Under **Choose a source**, select the **Kinesis Data Stream** radio button and choose `retail-trans` stream that you created earlier from the dropdown list. Click **Next**. If you do not see your data stream listed, make sure you are in Oregon region and your data stream from previous step is in Active state.
4. (Step 2: Process records) For **Transform source records with AWS Lambda** and **Convert record format**, leave both at `Disabled` and click **Next**.
5. (Step 3: Choose a destination) Select Amazon S3 as **Destination** and click `Create new` to create a new S3 bucket.
  S3 bucket names are globally unique, so choose a bucket name that is unique for you. You can call it `aws-analytics-immersion-day-xxxxxxxx` where `xxxxxxxx` is a series of random numbers or characters of your choice. You can use something like your name or your favorite number.
6. Under **S3 Prefix**, copy and paste the following text exactly as shown.
    Enter S3 prefix. For example, type as follows:
    ```buildoutcfg
    json-data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/
    ```

    At this point, you may see a message **You can't include expressions in the prefix unless you also specify an error prefix.** Ignore this, it will go away once you enter the error prefix in the next step.

    Under S3 error prefix, copy and paste the following text exactly as shown.
    ```buildoutcfg
    error-json/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/!{firehose:error-output-type}
    ```

    :warning: **S3 prefix or S3 error prefix pattern must not contain a new line(`\n`) character. If you have copied the example pattern and pasted it into the S3 prefix or S3 error prefix, it is a good idea to remove the trailing line breaks.**

    After entering S3 prefix and 3 error prefix, click **Next**. 
    (**cf.** [Custom Prefixes for Amazon S3 Objects](https://docs.aws.amazon.com/firehose/latest/dev/s3-prefixes.html))
7. (Step 4: Configure settings) Set buffer size to `1` MB and buffer interval to `60` seconds in **S3 buffer conditions**. Leave everything else as default.
8. Under **Permissions** IAM role, select **Create or update IAM role** and click the **Next** button.
 ![aws-kinesis-firehose-create_new_iam_role](./assets/aws-kinesis-firehose-create_new_iam_role.png)
9. (Step 5: Review) If there are no errors after checking the information entered in **Review**, click the **Create delivery stream** button to complete the **Firehose** creation.

\[[Top](#top)\]

## <a name="kinesis-data-pipeline"></a>Verify data pipeline operation
In this step, we will generate sample data and verify it is being processed and stored as follows- `Kinesis Data Streams -> Kinesis Data Firehose -> S3`.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. Connect SSH to the previously created E2 instance. You can go to the AWS Console and click the **Connect** button on the instance details page, or SSH from your local machine command line using the key pair you downloaded.
2. Run `gen_kinesis_data.py` script on the EC2 instance by entering the following command -
    ```shell script
    python3 gen_kinesis_data.py -I resources/online_retail.csv \
      --region-name us-west-2 \
      --service-name kinesis \
      --out-format json \
      --stream-name retail-trans
    ```
    If you would like to know more about the usage of this command, you can type
    ```shell script
    python3 gen_kinesis_data.py --help
    ```
3. Verify that data is generated every second. Let it run for a few minutes and terminate the script. You can enter `Ctrl+C` to end the script execution.
4. Go to **S3** service and open the bucket you created earlier. You can see that the original data has been delivered by **Kinesis Data Firehose** to S3 and stored in a folder structure by year, month, day, and hour.

\[[Top](#top)\]

## <a name="athena"></a>Analyze data using Athena
Using **Amazon Athena**, you can create tables based on data stored in S3, query those tables using SQL, and view query results.

First, create a database to query the data.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

### Step 1: Create a database
1. Go to **Athena** from the list of services on the AWS Management console.
2. The first time you visit Athena console, you will be taken to the **Get Started** page. Click the **Get Started** button to open the query editor.
3. If this is your first time using Athena, you need to first set an S3 location to save Athena's query results. Click the **set up a query result location in Amazon S3** box.
 ![aws-athena-setup-query-results-location-01](./assets/aws-athena-setup-query-results-location-01.png)
In this lab, we will create a new folder in the same S3 bucket you created in [\[Step-1b\] Create Kinesis Data Firehose to store data in S3](#kinesis-data-firehose) section.
For example, set your query location as `s3://aws-analytics-immersion-day-xxxxxxxx/athena-query-results/` (`xxxxxxxx` is the unique string you gave to your S3 bucket)
 ![aws-athena-setup-query-results-location-02](./assets/aws-athena-setup-query-results-location-02.png)
Unless you are visiting for the first time, Athena Query Editor is oppened.
4. You can see a query window with sample queries in the Athena Query Editor. You can start typing your SQL query anywhere in this window.
5. Create a new database called `mydatabase`. Enter the following statement in the query window and click the **Run Query** button.
    ```buildoutcfg
    CREATE DATABASE mydatabase
    ```
6. Confirm that the the dropdown list under **Database** section on the left panel has updated with a new database called  `mydatabase`. If you do not see it, make sure the **Data source** is selected to `AwsDataCatalog`.
 ![aws-athena-create-database](./assets/aws-athena-create-database.png)

### Step 2: Create a table
1. Make sure that `mydatabase` is selected in **Database**, and click the `+` button above the query window to open a new query.
2. Copy the following query into the query editor window, replace the `xxxxxxx` in the last line under `LOCATION` with the string of your S3 bucket, and click the **Run Query** button to execute the query to create a new table.
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
    If the query is successful, a table named `retail_trans_json` is created and displayed on the left panel under the **Tables** section.

    If you get an error, check if (a) you have updated the `LOCATION` to the correct S3 bucket name, (b) you have `mydatabase` selected under the **Database** dropdown, and (c) you have `AwsDataCatalog` selected as the **Data source**.
3. After creating the table, click the `+` button to create a new query. Run the following query to load the partition data.
    ```buildoutcfg
    MSCK REPAIR TABLE mydatabase.retail_trans_json
    ```

### Step 3: Query Data
+ Click the `+` button to open a new query tab. Enter the following SQL statement to query 10 transactions from the table and click **Run Query**.
    ```buildoutcfg
    SELECT *
    FROM retail_trans_json
    LIMIT 10
    ```
    The result is returned in the following format:
    ![aws_athena_select_all_limit_10](./assets/aws_athena_select_all_limit_10.png)

    You can experiment with writing different SQL statements to query, filter, sort the data based on different parameters.
    You have now learned how Amazon Athena allows querying data in Amazon S3 easily without requiring any database servers.

\[[Top](#top)\]

## <a name="amazon-quicksight-visualization"></a>Data visualization with QuickSight

In this section, we will use Amazon QuickSight to visualize the data that was collected by Kinesis, stored in S3, and analyzed using Athena previously.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. Go to [QuickSight Console](https://quicksight.aws.amazon.com).
2. Click the **Sign up for QuickSight** button to sign up for QuickSight.
3. Select Standard Edition and click the **Continue** button.
4. Specify a QuickSight account name. This name should be unique to you, so use the unique string in the account name similar to how you did for the S3 bucket name earlier. Enter your personal email address under **Notification email address**.
5. QuckSight needs access to S3 to be able to read data. Check the **Amazon S3** box, and select `aws-analytics-immersion-day-xxxxxxxx` bucket from the list. Click **Finish**.
   ![aws-quicksight-choose-s3-bucket](./assets/aws-quicksight-choose-s3-bucket.png)
6. After the account is created, click the **Go to Amazon QuickSight** button. Confirm that you are in `US West (Oregon)` region. Click on the account name on the top right corner and select **US West (Oregon)** if it is not already set to Oregon. Click the **New Analysis** button and click on **New dataset** on the next screen.
   ![aws-quicksight-new_data_sets](./assets/aws-quicksight-new_data_sets.png)
7. Click `Athena` and enter `retail-quicksight` in the Data source name in the pop-up window.
Click **Validate connection** to change to `Validated`, then click the **Create data source** button.
   ![aws-quicksight-athena_data_source](./assets/aws-quicksight-athena_data_source.png)
8. On the **Choose your table** screen, select Catalog `AwsDataCatalog`, Database `mydatabase` and Tables `retail_trans_json`. Click the **Select** button.
   ![aws-quicksight-athena-choose_your_table](./assets/aws-quicksight-athena-choose_your_table.png)
9. On the **Finish dataset creation** screen, choose `Directly query your data` and click the **Visualize** button.
   ![aws-quicksight-finish-dataset-creation](./assets/aws-quicksight-finish-dataset-creation.png)
10. Let's visualize the `Quantity` and `Price` by `InvoiceDate`. Select vertical bar chart from the **Visual types** box on the bottom left. In the **field wells**, drag `invoicedate` from the left panel into **X axis**, drag `price`, and `quantity` into **Value**. You will see a chart get populated as shown below.
   ![aws-quicksight-bar-chart](./assets/aws-quicksight-bar-chart.png)
11. Let's share the Dashboard we just created with other users. Click on the account name on the top right corner and select **Manage QuickSight**.
12. Click the `+` button on the right side, and enter an email address of the person with whom you want to share the visualization. Click the **Invite** button and close the popup window.</br>
   ![aws-quicksight-user-invitation](./assets/aws-quicksight-user-invitation.png)
13. Users you invite will receive the following Invitation Email. They can click the button to accept invitation.
   ![aws-quicksight-user-email](./assets/aws-quicksight-user-email.png)
14. Return to the QuickSight home screen, select your analysis, and click **Share> Share analysis** from the upper right corner.
   ![aws-quicksight-share-analysis](./assets/aws-quicksight-share-analysis.png)
15. Select `BI_user01` and click the Share button.
   ![aws-quicksight-share-analysis-users](./assets/aws-quicksight-share-analysis-users.png)
16. Users receive the following email: You can check the analysis results by clicking **Click to View**.
   ![aws-quicksight-user-email-click-to-view](./assets/aws-quicksight-user-email-click-to-view.png)

\[[Top](#top)\]

## <a name="athena-ctas-lambda-function"></a>(Optional) Combine small files stored in S3 into large files using AWS Lambda Function

When real-time incoming data is stored in S3 using Kinesis Data Firehose, files with small data size are created.
To improve the query performance of Amazon Athena, it is recommended to combine small files into one large file.
To run these tasks periodically, we are going to create an AWS Lambda function function that executes Athena's Create Table As Select (CTAS) query.

![aws-analytics-system-build-steps-extra](./assets/aws-analytics-system-build-steps-extra.svg)

### Step 1: Create a table to store CTAS query results
1. Access **Athena Console** and go to the Athena Query Editor.
2. Select mydatabase from **DATABASE** and navigate to **New Query**.
3. Enter the following CREATE TABLE statement in the query window and select **Run Query**.<br/>
In this exercise, we will change the json format data of the `retal_tran_json` table into parquet format and store it in a table called `ctas_retail_trans_parquet`.<br/>
The data in the `ctas_retail_trans_parquet` table will be saved in the location `s3://aws-analytics-immersion-day-xxxxxxxx/parquet-retail-trans` of the S3 bucket created earlier.
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

### Step 2: Create an AWS Lambda Function
1. Open the **AWS Lambda Console**.
2. Select **Create a function**.
3. Enter `MergeSmallFiles` for Function name.
4. Select `Python 3.8` in Runtime.
5. Select **Create a function**.
 ![aws-athena-ctas-lambda-create-function](./assets/aws-athena-ctas-lambda-create-function.png)
6. Select **Add trigger** in the Designer tab.
7. Select **CloudWatch Events/EventBridge** in `Select a trigger` of **Trigger configuration**.
Select `Create a new rule` in Rule and enter the appropriate rule name (eg `MergeSmallFilesEvent`) in Rule name.
Select `Schedule expression` as the rule type, and enter `cron(5 * * * *)` for running the task every 5 minutes in the schedule expression.
 ![aws-athena-ctas-lambda-add-trigger](./assets/aws-athena-ctas-lambda-add-trigger.png)
8. In **Trigger configuration**, click **\[Add\]**.
9. Copy and paste the code from the `athena_ctas.py` file into the code editor of the Function code. Click **Deploy**.
10. Click **\[Add environment variables\]** to register the following environment variables.
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
    For example, set Environment variables as follows:
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
11. To add the IAM Policy required to execute Athena queries, click `View the MergeSmallFiles-role-XXXXXXXX role on the IAM console.` in the Execution role and modify the IAM Role.
 ![aws-athena-ctas-lambda-execution-iam-role](./assets/aws-athena-ctas-lambda-execution-iam-role.png)
12. After clicking the **Attach policies** button in the **Permissions** tab of IAM Role, add **AmazonAthenaFullAccess** and **AmazonS3FullAccess** in order.
 ![aws-athena-ctas-lambda-iam-role-policies](./assets/aws-athena-ctas-lambda-iam-role-policies.png)
13. Select **Edit** in Basic settings. Adjust Memory and Timeout appropriately. In this lab, we set Timout to `5 min`.

\[[Top](#top)\]

## <a name="amazon-es"></a>Create Amazon Elasticsearch Service for Real-Time Data Analysis

An Elasticsearch cluster is created to store and analyze data in real time. Amazon ES domains are synonymous with Elasticsearch clusters. A domain is a setting that specifies a setting, instance type, number of instances, and storage resources.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. In the AWS Management Console, select the **Elasticsearch** service in the Analytics category. 
2. (Step 1: Choose deployment type) Select **Create a new domain**.
3. On the **Create Elasticsearch domain** page, select **Production** for **Deployment type**.
 ![amazon-es-deployment-type](./assets/amazon-es-deployment-type.png)
4. For **Version**, choose the Elasticsearch version for your domain. We recommend that you choose the latest supported version. For more information, see [Supported Elasticsearch Versions](https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/what-is-amazon-elasticsearch-service.html#aes-choosing-version). 
5. Click **Next** button.
6. (Step 2: Configure domain) Enter the name of the domain. In this lab, `retail` will be used as the example domain name.
7. For **Instance type**, choose the instance type of your Amazon ES domain. In this lab, it is recommended to use a small, economical instance type (`t3.medium.elasticsearch`) suitable for testing purposes. 
8. Enter the desired number of instances in **Number of nodes**. In this lab, we will use the default value of `3`.
9. Select EBS for **Data nodes storage type**.
    + a. Select General Purpose (SSD) for the **EBS volume type**. For more information, see Amazon EBS Volume Types.
    + b. In EBS volume size, enter the **EBS storage size per node** for each data node in GiB. In this lab, we will use the default value of `10`. 
    ![amazon-es-config-domain](./assets/amazon-es-config-domain.png)
10. For now, you can ignore the **Dedicated master nodes, Snapshot configuration** and **Optional Elasticsearch cluster settings** sections.
11. Click **Next**.
12. (Step 3: Configure access and security) For **Network configuration**, select **VPC access**. Choose the appropriate VPC and subnet. Select the `es-cluster-sg` created in the preparation step as Security Groups.
13. For now, disable **Amazon Cognito Authentication** and **Fine–grained access control**.
 ![amazon-es-access-control](./assets/amazon-es-access-control.png)
14. For **Access policy**, select **JSON defined access policy** from **Domain access policy**, and then create and enter a **JSON defined access policy** using the following template in **Add or edit the access policy**.
    + JSON defined access policy Template - Enter the domain name entered in **(Step 2: Configure domain)** in `<DOMAIN-NAME>`.
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
    + ex) In this lab, we used `retail` as the domain name, so we create a JSON defined access policy as shown below.
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
    + Once **JSON defined access policy** has been created, you will see the following screen.
    ![amazon-es-json-access-policy](./assets/amazon-es-json-access-policy.png)
15. **Encryption** only allows **Require HTTPS for all traffic to the domain**, and other items are disabled.
 ![amazon-es-encryption-config](./assets/amazon-es-encryption-config.png)
16. Keep all default values ​​of **Encryption**. Select **Next**.
17. On the **Review** page, review your domain configuration and then choose **Confirm**.

\[[Top](#top)\]

## <a name="amazon-lambda-function"></a>Ingest real-time data into ElasticSearch using AWS Lambda Functions

You can index data into Amazon Elasticsearch Service in real time using a Lambda function.
In this lab, you will create a Lambda function using the AWS Lambda console.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

### To add a common library to Layers for use by Lambda functions,
1. Open the **AWS Lambda Console**.
2. Enter the **Layers** menu and select **Create layer**.
3. Enter `es-lib` for the Name.
4. Select `Upload a file from Amazon S3` and enter the s3 link url where the library code is stored or the compressed library code file.
For how to create `es-lib.zip`, refer to [Example of creating a Python package to register in AWS Lambda Layer](#aws-lambda-layer-python-packages).
5. Select `Python 3.8` from `Compatible runtimes`.

### To create a Lambda function,
1. Open the **AWS Lambda Console**.
2. Select **Create a function**.
3. Enter `UpsertToES` for Function name.
4. Select `Python 3.8` in Runtime.
5. Select **Create a function**.
 ![aws-lambda-create-function](./assets/aws-lambda-create-function.png)
6. Select **\[Add trigger\]** in the Designer tab. In Layers, choose **Add a layer**.
7. Select `Custome Layers` in **Choose a Layer** section, and choose Name and Version of the previously created layer as Name and Version in **Custom layers**.
 ![aws-lambda-add-layer-to-function](./assets/aws-lambda-add-layer-to-function.png)
8. Click **Add**.
9. Select `UpsertToES` in the Designer tab to return to Function code and Configuration.
10. Copy and paste the code from the `upsert_to_es.py` file into the code editor of the Function code. Click **Deploy**
11. In Environment variables, click **Edit**.
12. Click **Add environment variables** to register the following 4 environment variables.
    ```shell script
    ES_HOST=<elasticsearch service domain>
    ES_INDEX=<elasticsearch index name>
    ES_TYPE=<elasticsearch type name>
    REQUIRED_FIELDS=<columns to be used as primary key>
    REGION_NAME=<region-name>
    DATE_TYPE_FIELDS=<columns of which data type is either date or timestamp>
    ```
    For example, set Environment variables as follows:
    ```buildoutcfg
    ES_HOST=vpc-retail-xkl5jpog76d5abzhg4kyfilymq.us-west-1.es.amazonaws.com
    ES_INDEX=retail
    ES_TYPE=trans
    REQUIRED_FIELDS=Invoice,StockCode,Customer_ID
    REGION_NAME=us-west-2
    DATE_TYPE_FIELDS=InvoiceDate
    ```
13. Click **Save**.
14. In order to execute the lambda function in the VPC and read data from Kinesis Data Streams, you need to add the IAM Policy required for the Execution role required to execute the lamba function.
Click `View the UpsertToES-role-XXXXXXXX role on the IAM console.` to edit the IAM Role.
 ![aws-lambda-execution-iam-role](./assets/aws-lambda-execution-iam-role.png)
15. After clicking the **Attach policies** button in the **Permissions** tab of IAM Role, add **AWSLambdaVPCAccessExecutionRole** and **AmazonKinesisReadOnlyAccess** in order.
 ![aws-lambda-iam-role-policies](./assets/aws-lambda-iam-role-policies.png)
16. Click the **Edit** button in the VPC category to go to the Edit VPC screen. Select `Custom VPC` for VPC connection.
Choose the VPC and subnets where you created the domain for the Elasticsearch service, and choose the security groups that are allowed access to the Elasticsearch service domain.
17. Select **Edit** in Basic settings. Adjust Memory and Timeout appropriately. In this lab, we set Timout to `5 min`.
18. Go back to the Designer tab and select **Add trigger**.
19. Select **Kinesis** from `Select a trigger` in the **Trigger configuration**.
20. Select the Kinesis Data Stream (`retail-trans`) created earlier in **Kinesis stream**.
21. Click **Add**.
 ![aws-lambda-kinesis](./assets/aws-lambda-kinesis.png)

\[[Top](#top)\]

## <a name="amazon-es-kibana-visualization"></a>Data visualization with Kibana

Visualize data collected from Amazon Elasticsearch Service using Kibana.

![aws-analytics-system-build-steps](./assets/aws-analytics-system-build-steps.svg)

1. The Amazon Elasticsearch cluster is provisioned in a VPC. Hence, the Amazon Elasticsearch endpoint and the Kibana endpoint are not available over the internet. In order to access the endpoints, we have to create a ssh tunnel and do local port forwarding. <br/>
For Winodws, refer to [here](#SSH-Tunnel-with-PuTTy-on-Windows).</br>
For Mac/Linux, to access the Elasticsearch Cluster, add the ssh tunnel configuration to the ssh config file of the personal local PC as follows.<br/>
    ```shell script
    # Elasticsearch Tunnel
    Host estunnel
      HostName <EC2 Public IP of Bastion Host>
      User ec2-user
      IdentitiesOnly yes
      IdentityFile ~/.ssh/analytics-hol.pem
      LocalForward 9200 <Elasticsearch Endpoint>:443
    ```
  + **EC2 Public IP of Bastion Host** uses the public IP of the EC2 instance created in the **Lab setup** step.
  + ex)
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
2. Run `ssh -N estunnel` in Terminal.
3. Connect to `https://localhost:9200/_plugin/kibana/` in a web browser.
4. (Home) Click **Use Elasticsearch data / Connect to your Elasticsearch index** in **Add Data to Kibana**.
 ![kibana-01-add_data](./assets/kibana-01-add_data.png)
5. (Management / Create index pattern) In **Step 1 of 2: Define index pattern** of **Create index pattern**, enter `retail*` in Index pattern.
 ![kibana-02a-create-index-pattern](./assets/kibana-02a-create-index-pattern.png)
6. (Management / Create index pattern) Choose **> Next step**.
7. (Management / Create index pattern) Select `InvoiceDate` for the Time Filter field name in **Step 2 of 2: Configure settings** of the Create index pattern.
 ![kibana-02b-create-index-pattern-configure-settings](./assets/kibana-02b-create-index-pattern-configure-settings.png)
8. (Management / Create index pattern) Click **Create index pattern**.
 ![kibana-02c-create-index-pattern-review](./assets/kibana-02c-create-index-pattern-review.png)
9. (Management / Advanced Settings) After selecting **Advanced Settings** from the left sidebar menu, set **Timezone for date formatting** to `Etc/UTC`. Since the log creation time of the test data is based on `UTC`, **Kibana**'s **Timezone** is also set to `UTC`.
 ![kibana-02d-management-advanced-setting](./assets/kibana-02d-management-advanced-setting.png)
10. (Discover) After completing the creation of **Index pattern**, select **Discover** to check the data collected in Elasticsearch.
 ![kibana-03-discover](./assets/kibana-03-discover.png)
11. (Discover) Let's visualize the `Quantity` by `InvoicdDate`. Select **invoicdDate** from **Available fields** on the left, and click **Visualize** at the bottom.
 ![kibana-04-discover-visualize](./assets/kibana-04-discover-visualize.png)
12. (Visualize) After selecting **Y-Axis** in **Metrics** on the Data tab, apply `Sum` for **Aggregation**, and `Quantity` for **Field** as shown below.
 ![kibana-05-discover-change-metrics](./assets/kibana-05-discover-change-metrics.png)
13. (Visualize) Click **Save** in the upper left corner, write down the name of the graph you saved, and then click **Confirm Save**.
 ![kibna-08-visualize-save](./assets/kibana-08-visualize-save.png)
14. (Dashboards) Click **Dashboard** icon on the left and click the **Create new dashboard** button.
 ![kibana-09-dashboards](./assets/kibana-09-dashboards.png)
15. (Dashboards) Click **Add** on the upper left, and select the graph created in the previous step in **Add Panels**.
 ![kibana-10-import-visualization](./assets/kibana-10-import-visualization.png)
16. (Dashboards) Click **Save** at the top left, enter **Title** in the **Save dashboard**, and click **Confirm Save**.
![kibana-12-discover-save-dashboard](./assets/kibana-12-discover-save-dashboard.png)
17. (Dashboards) You can see the following Dashboards.
 ![kibana-13-complete](./assets/kibana-13-complete.png)

\[[Top](#top)\]

## Recap and Review

:warning: **At the end of this lab, you should delete the resources you used to avoid incurring additional charges for the AWS account you used.**

Through this lab, we have built a Business Intelligent System with Lambda Architecture such that consists of real-time data processing and batch data processing layers.

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
    + <a name="aws-lambda-layer-python-packages"></a>Example of creating a python package to register with AWS Lambda layer: **elasticsearch**

      :warning: **You should create the python package on Amazon Linux, otherwise create it using a simulated Lambda environment with Docker.**
      <pre>
      [ec2-user@ip-172-31-6-207 ~] $ python3 -m venv es-lib
      [ec2-user@ip-172-31-6-207 ~] $ cd es-lib
      [ec2-user@ip-172-31-6-207 ~] $ source bin/activate
      (es-lib) $ mkdir -p python_modules
      (es-lib) $ pip install 'elasticsearch>=7.0.0,< 7.11' requests requests-aws4auth -t python_modules
      (es-lib) $ mv python_modules python
      (es-lib) $ zip -r es-lib.zip python/
      (es-lib) $ aws s3 mb s3://my-bucket-for-lambda-layer-packages
      (es-lib) $ aws s3 cp es-lib.zip s3://my-bucket-for-lambda-layer-packages/var/
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

:warning: **At the end of this lab, you should delete the resources you used to avoid incurring additional charges for the AWS account you used.**

Introducing how to deploy using the AWS CDK.

### Prerequisites
1. Install AWS CDK Toolkit.

    ```shell script
    npm install -g aws-cdk
    ```

2. Verify that cdk is installed properly by running the following command:
    ```
    cdk --version
    ```
   ex)
    ```shell script
    $ cdk --version
    2.41.0 (build 56ba2ab)
    ```

##### Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

\[[Top](#top)\]

### Deployment

When deployed as CDK, `1(a), 1(b), 1(c), 1(f), 2(b), 2(a)` in the architecture diagram below are automatically created.

![aws-analytics-system-build-steps-extra](./assets/aws-analytics-system-build-steps-extra.svg)

1. Refer to [Getting Started With the AWS CDK](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html) to install cdk. 
Create an IAM User to be used when running cdk and register it in `~/.aws/config`. (**cf.** [Creating an IAM User](#preliminaries))<br/>
For example, after creating an IAM User called cdk_user, add it to `~/.aws/config` as shown below.

    ```shell script
    $ cat ~/.aws/config
    [profile cdk_user]
    aws_access_key_id=AKIAIOSFODNN7EXAMPLE
    aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    region=us-east-1
    ```

2. Create a Python package to register in the Lambda Layer and store it in the s3 bucket. For example, create an s3 bucket named `lambda-layer-resources` so that you can save the elasticsearch package to register in the Lambda Layer as follows.

    ```shell script
    $ aws s3 ls s3://lambda-layer-resources/var/
    2019-10-25 08:38:50          0
    2019-10-25 08:40:28    1294387 es-lib.zip
    ```

3. After downloading the source code from git, enter the s3 bucket name where the package to be registered in the lambda layer is stored in an environment variable called `S3_BUCKET_LAMBDA_LAYER_LIB`.
After setting, deploy using the `cdk deploy` command. 

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
    (.env) $ cdk --profile cdk_user deploy --require-approval never --all
    ```

   :white_check_mark: `cdk bootstrap ...` command is executed only once for the first time to deploy **CDK toolkit stack**, and for subsequent deployments, you only need to execute `cdk deploy` command without distributing **CDK toolkit stack**.

    ```shell script
    (.env) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    (.env) $ export CDK_DEFAULT_REGION=us-west-2
    (.env) $ export S3_BUCKET_LAMBDA_LAYER_LIB=lambda-layer-resources
    (.env) $ cdk --profile cdk_user deploy --require-approval never --all
    ```

4. To delete the deployed application, execute the `cdk destroy` command as follows.
    ```shell script
    (.env) $ cdk --profile cdk_user destroy --force --all
    ```

\[[Top](#top)\]

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
