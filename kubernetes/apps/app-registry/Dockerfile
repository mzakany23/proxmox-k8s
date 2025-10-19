FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod ./
COPY main.go ./
RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux go build -o app-registry

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/app-registry .
RUN mkdir -p /data
EXPOSE 8080
CMD ["./app-registry"]
