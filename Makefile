# Variables
API_URL = $(shell pulumi stack output api_url)
LAMBDA_NAME = $(shell pulumi stack output lambda_name)
LOG_GROUP = /aws/lambda/$(LAMBDA_NAME)

.PHONY: upload-cv help logs logs-tail

help:
	@echo "Available commands:"
	@echo "  make upload-cv    Upload test_cv.pdf to the API"
	@echo "  make logs        Show all Lambda logs from the last 1 hour"
	@echo "  make logs-tail   Watch Lambda logs in real-time"
	@echo "  make help        Show this help message"

upload-cv:
	@if [ ! -f test_cv.pdf ]; then \
		echo "Error: test_cv.pdf not found in current directory"; \
		exit 1; \
	fi
	@echo "Uploading test_cv.pdf to $(API_URL)..."
	@base64 -i test_cv.pdf > test_cv.b64
	@curl -v -X POST $(API_URL) \
		-H "Content-Type: application/pdf" \
		-H "Content-Disposition: attachment; filename=test_cv.pdf" \
		--data-binary "@test_cv.b64"
	@rm test_cv.b64

logs:
	@echo "Fetching logs from $(LOG_GROUP)..."
	@aws logs get-log-events \
		--log-group-name $(LOG_GROUP) \
		--log-stream-name $$(aws logs describe-log-streams \
			--log-group-name $(LOG_GROUP) \
			--order-by LastEventTime \
			--descending \
			--max-items 1 \
			--query 'logStreams[0].logStreamName' \
			--output text) \
		--query 'events[*].message' \
		--output text

logs-tail:
	@echo "Watching logs from $(LOG_GROUP)..."
	@aws logs tail $(LOG_GROUP) --follow