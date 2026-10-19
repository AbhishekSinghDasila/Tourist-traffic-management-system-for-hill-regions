# Build upstream community sources because the public prebuilt images were removed.
FROM golang:1.24-alpine AS server-build
RUN CGO_ENABLED=0 go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z

FROM golang:1.24-alpine AS client-build
RUN CGO_ENABLED=0 go install github.com/minio/mc@RELEASE.2025-08-13T08-35-41Z

FROM alpine:3.22 AS runtime
RUN apk add --no-cache ca-certificates curl

FROM runtime AS server
COPY --from=server-build /go/bin/minio /usr/local/bin/minio
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]

FROM runtime AS client
COPY --from=client-build /go/bin/mc /usr/local/bin/mc
ENTRYPOINT ["mc"]
