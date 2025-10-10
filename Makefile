ifneq (,$(wildcard ./.env))
include .env
export 
ENV_FILE_PARAM = --env-file .env

endif

build:
	docker-compose up --build -d --remove-orphans

up:
	docker-compose up -d

down:
	docker-compose down

show-logs:
	docker-compose logs

serv:
	uvicorn src:app --reload
# 	python -m uvicorn src:app --reload

act:
	.\env\Scripts\activate

reqn:
	pip install -r requirements.txt

ureqn:
	pip freeze > requirements.txt

alembic_init:
	alembic init app/db/migrations

# mmig: 
# 	if [ -z "$(message)" ]; then \
# 		alembic revision --autogenerate; \
# 	else \
# 		alembic revision --autogenerate -m "$(message)"; \
# 	fi

mmig: 
	alembic revision --autogenerate -m "$(message)"

mmig-auto:
	alembic revision --autogenerate
	
mig:
	alembic upgrade head

# initial_data:
# 	python initials/initial_data.py

# tests:
# 	pytest --disable-warnings -vv -x