# Go Multi-Stage Dockerfile
# Replace REPLACE_PORT with your application's port (e.g., 8080)

# ============================================
# Build Stage
# ============================================
FROM golang:1.22-alpine as builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache git ca-certificates

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags='-w -s -extldflags "-static"' \
    -o /app/server .

# ============================================
# Runtime Stage
# ============================================
FROM scratch

WORKDIR /app

# Copy CA certificates for HTTPS
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy binary from builder
COPY --from=builder /app/server /app/server

# Expose application port
EXPOSE REPLACE_PORT

# Run application
ENTRYPOINT ["/app/server"]
