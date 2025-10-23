# scripts/init_hadoop.sh
#!/bin/bash

echo "🔧 INICIALIZANDO HADOOP DESDE CERO..."

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH

# Crear enlace simbólico para Java
ln -sf /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/java-8-openjdk-amd64 2>/dev/null || true

# Formatear NameNode (solo si no existe)
echo "📝 FORMATEANDO NAMENODE..."
hdfs namenode -format -force -nonInteractive

echo "✅ NameNode formateado"