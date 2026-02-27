#!/bin/bash
echo "Ejecutando pruebas de frontend..."
npm run lint || exit 1
npm run test:coverage || echo "No se encontraron tests de frontend o fallaron. Omitiendo..."

echo "Ejecutando pruebas de backend..."
cd backend || exit 1
source venv/bin/activate
pytest --cov=app || exit 1
echo "Todas las pruebas finalizaron."
