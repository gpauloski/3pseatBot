APP_NAME=discord_bot

RUN_CMD="python --version ; pip install -e . ; python run.py --config config.json"

docker-build:
	docker image build -t $(APP_NAME) .

docker-interactive:
	docker run --rm --entrypoint=/bin/bash -v $(shell pwd):/bot \
		-w /bot -it -p 5000:5000 --name=$(APP_NAME) $(APP_NAME)

docker-start:
	docker run -v $(shell pwd):/bot -d --restart=unless-stopped \
		-w /bot -p 5000:5000 --name=$(APP_NAME) $(APP_NAME) /bin/bash -c $(RUN_CMD)

docker-stop:
	docker stop $(APP_NAME) || true;
	docker rm $(APP_NAME) || true

dev-start:
	eval $(RUN_CMD)

lint:
	black threepseat run.py
	flake8 . --count --show-source --statistics
	flake8 run.py --count --show-source --statistics

docs:
	cd docs ; make html ; cd ..
