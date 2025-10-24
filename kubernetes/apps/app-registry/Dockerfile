FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o app-registry

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/app-registry .
COPY --from=builder /app/apps.json /root/apps.json
COPY --from=builder /app/entrypoint.sh /root/entrypoint.sh
RUN mkdir -p /data && chmod +x /root/entrypoint.sh
EXPOSE 8080
CMD ["/root/entrypoint.sh"]
