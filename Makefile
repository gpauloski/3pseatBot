APP_NAME=3pseatBot

RUN_CMD="python run.py --config config.json"

docker-build:
	docker image build -t $(APP_NAME) .

docker-interactive:
	docker run --rm --entrypoint=/bin/bash -v $(shell pwd):/bot \
		-w /bot -it --name=$(APP_NAME) $(APP_NAME)

docker-start:
	docker run -v $(shell pwd):/bot -d --restart=unless-stopped \
		--name=$(APP_NAME) $(APP_NAME) $(RUN_CMD)

docker-stop:
	docker stop $(APP_NAME) || true;
	docker rm $(APP_NAME) || true

dev-start:
	$(RUN_CMD)