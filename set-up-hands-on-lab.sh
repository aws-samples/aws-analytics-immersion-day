#!/bin/bash -

WORK_DIR=$(cd $(dirname $0); pwd)
TARGET_DIR=$(dirname ${WORK_DIR})

OS_NAME=$(cat /etc/os-release | awk -F "=" '$1 == "NAME" { print $2 }')
if [[ z"${OS_NAME}" == z"\"Amazon Linux AMI\"" ]];
then
  sudo yum -y update
  sudo yum -y install python36

  sudo pip-3.6 install -U boto3
  sudo pip-3.6 install csvkit
elif [[ z"${OS_NAME}" == z"\"Amazon Linux\"" ]];
then
  sudo yum -y update
  sudo yum -y install python3

  sudo pip3 install -U boto3
  sudo pip3 install csvkit
elif [[ z"${OS_NAME}" == z"\"Ubuntu\"" ]];
then
  sudo apt-get -y update
  sudo apt-get -y install python3.6
  sudo apt-get -y install python3-pip

  sudo pip3 install -U boto3
  sudo pip3 install csvkit
else
  echo "[Unknown OS] You should install python3.6+, pip3+ for yourself!"
  exit 0
fi

ln -sf ${WORK_DIR}/src/main/python/UpsertToES/upsert_to_es.py ${TARGET_DIR}/upsert_to_es.py
ln -sf ${WORK_DIR}/src/main/python/MergeSmallFiles/athena_ctas.py ${TARGET_DIR}/athena_ctas.py
ln -sf ${WORK_DIR}/src/main/python/utils/gen_kinesis_data.py ${TARGET_DIR}/gen_kinesis_data.py

mkdir -p ${WORK_DIR}/resources
pushd ${WORK_DIR}/resources
wget 'https://archive.ics.uci.edu/ml/machine-learning-databases/00502/online_retail_II.xlsx'
in2csv online_retail_II.xlsx > online_retail.csv
head online_retail.csv > sample_online_retail.csv
popd

ln -sf ${WORK_DIR}/resources ${TARGET_DIR}/resources

