#!/bin/bash
# Corregir variables de entorno
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# Instalar PySpark
pip3 install pyspark==3.5.1

# Configurar Hadoop para usar Java 11
echo "export JAVA_HOME=$JAVA_HOME" >> /opt/hadoop/etc/hadoop/hadoop-env.sh

# Formatear e iniciar HDFS
/opt/hadoop/bin/hdfs namenode -format -force
/opt/hadoop/sbin/start-dfs.sh
/opt/hadoop/sbin/start-yarn.sh
