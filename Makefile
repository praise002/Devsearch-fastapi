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

show_logs:
	docker-compose logs

serv:
	uvicorn src:app --reload
# 	python -m uvicorn src:app --reload

create_env:
	python3.12 -m venv venv

# act:  # doesn't work
# 	source venv/bin/activate

reqn:
	pip install -r requirements.txt

ureqn:
	pip freeze > requirements.txt

alembic_init:
	alembic init app/db/migrations

mmig: 
	if [ -z "$(message)" ]; then \
		alembic revision --autogenerate; \
	else \
		alembic revision --autogenerate -m "$(message)"; \
	fi


mmig_auto:
	alembic revision --autogenerate
	
mig:
	alembic upgrade head

# initial_data:
# 	python initials/initial_data.py

tests:
	pytest --disable-warnings -vv -x -s

random_s:
	python -c "import secrets; print(secrets.token_urlsafe(32))"

# Run all auth tests
# pytest tests/test_auth/ -v

# # Run only registration tests
# pytest tests/test_auth/test_register.py -v

# # Run with coverage
# pytest tests/test_auth/test_register.py --cov=src.auth --cov-report=html
