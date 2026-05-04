FROM eclipse-temurin:25-jdk-alpine AS builder

WORKDIR /builder

ARG JAR_FILE=./target/*.jar

COPY ${JAR_FILE} application.jar

RUN java -Djarmode=tools -jar application.jar extract --layers --destination extracted


FROM eclipse-temurin:25-jre-alpine

WORKDIR /app

ARG EXTRACTED_PATH=/builder/extracted

COPY --from=builder $EXTRACTED_PATH/dependencies/ ./
COPY --from=builder $EXTRACTED_PATH/spring-boot-loader/ ./
COPY --from=builder $EXTRACTED_PATH/snapshot-dependencies/ ./
COPY --from=builder $EXTRACTED_PATH/application/ ./

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "application.jar"]