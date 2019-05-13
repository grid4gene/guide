# set the environment for the hadoop and spark and gatk
# create a symbol link for the gatk, hadoop and spark in the TOP_DIR

# PATH for the SPARK related tools
export TOP_DIR=/mnt/disk_a/spark_tools

# GATK tool path
export PATH=$TOP_DIR/gatk:$PATH

## JAVA env variables
export JAVA_HOME=/usr/java/jdk1.8.0_162/jre
export PATH=$PATH:$JAVA_HOME/bin
export CLASSPATH=.:$JAVA_HOME/lib:$JAVA_HOME/lib/tools.jar

## HADOOP env variables
export HADOOP_HOME=$TOP_DIR/hadoop
export HADOOP_COMMON_HOME=$HADOOP_HOME
export HADOOP_HDFS_HOME=$HADOOP_HOME
export HADOOP_MAPRED_HOME=$HADOOP_HOME
export HADOOP_YARN_HOME=$HADOOP_HOME
export HADOOP_OPTS="-Djava.library.path=$HADOOP_HOME/lib/native"
export HADOOP_COMMON_LIB_NATIVE_DIR=$HADOOP_HOME/lib/native
export PATH=$PATH:$HADOOP_HOME/sbin:$HADOOP_HOME/bin
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export YARN_CONF_DIR=$HADOOP_HOME/etc/hadoop
export LD_LIBRARY_PATH=$HADOOP_HOME/lib/native:$LD_LIBRARY_PATH

## SPARK env variables
export SPARK_HOME=$TOP_DIR/spark
export PATH=$PATH:$SPARK_HOME/bin
export SPARK_DIST_CLASSPATH=$(hadoop classpath)
