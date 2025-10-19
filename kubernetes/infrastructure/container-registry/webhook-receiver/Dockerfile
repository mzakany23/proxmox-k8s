# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod ./
COPY main.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -o webhook-receiver .

# Runtime stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

COPY --from=builder /app/webhook-receiver .

EXPOSE 8080

CMD ["./webhook-receiver"]
