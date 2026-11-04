# Aplicación trasladada

El código Maven, las clases Java y las pruebas ahora están en
[`app/flink-transactions/`](../../app/flink-transactions/).
Los JSON locales del usuario y los builds anteriores se conservaron aquí.

Compilar desde la raíz con:

```powershell
mvn -B -ntp -f app/flink-transactions/pom.xml clean package
```
