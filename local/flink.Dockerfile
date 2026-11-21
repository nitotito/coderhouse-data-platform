FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY flink-app/pom.xml .
RUN mvn -q dependency:go-offline
COPY flink-app/src ./src
RUN mvn -q -DskipTests package
FROM flink:2.2.1-scala_2.12-java17
COPY --from=build /build/target/flink-transactions-1.2.0.jar /opt/flink/usrlib/job.jar
USER root
RUN mkdir -p /opt/flink/checkpoints && chown -R flink:flink /opt/flink/checkpoints
USER flink
