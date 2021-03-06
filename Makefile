APP_NAME=3pseatbot

docker-build:
	docker image build -t $(APP_NAME) .

docker-interactive:
	docker run --rm --entrypoint=/bin/bash -v $(shell pwd):/bot \
		-w /bot -it --name=$(APP_NAME) $(APP_NAME)

docker-start:
	docker run -v $(shell pwd):/bot -d --restart=unless-stopped \
		--name=$(APP_NAME) $(APP_NAME)

docker-stop:
	docker stop $(APP_NAME) || true;
	docker rm $(APP_NAME) || true

dev-start:
	cd 3pseatBot; python main.py

requirements:
	pip freeze > requirements.txt
