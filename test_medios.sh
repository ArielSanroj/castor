#!/bin/bash

echo "🧪 Pruebas de CASTOR Medios"
echo "============================"
echo ""

# Test 1: Análisis básico
echo "📊 Test 1: Análisis básico con tema Seguridad"
curl -s -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Colombia",
    "topic": "Seguridad",
    "max_tweets": 15,
    "time_window_days": 7
  }' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'✅ Success: {d.get(\"success\")}'); print(f'📊 Tweets analizados: {d.get(\"metadata\", {}).get(\"tweets_analyzed\", 0)}'); print(f'📝 Overview: {d.get(\"summary\", {}).get(\"overview\", \"N/A\")[:100]}...')"
echo ""

# Test 2: Sin tema específico
echo "📊 Test 2: Análisis sin tema específico"
curl -s -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bogotá",
    "max_tweets": 15
  }' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'✅ Success: {d.get(\"success\")}'); print(f'📊 Tweets analizados: {d.get(\"metadata\", {}).get(\"tweets_analyzed\", 0)}'); print(f'📍 Location: {d.get(\"metadata\", {}).get(\"location\", \"N/A\")}')"
echo ""

# Test 3: Validación de límites
echo "📊 Test 3: Validación - max_tweets fuera de rango"
curl -s -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Colombia",
    "max_tweets": 25
  }' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'❌ Success: {d.get(\"success\")}'); print(f'⚠️  Error: {d.get(\"error\", \"N/A\")[:100]}')"
echo ""

# Test 4: Con candidato
echo "📊 Test 4: Análisis con candidato"
curl -s -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Colombia",
    "topic": "Educación",
    "candidate_name": "Test Candidate",
    "max_tweets": 15
  }' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'✅ Success: {d.get(\"success\")}'); print(f'📊 Tweets analizados: {d.get(\"metadata\", {}).get(\"tweets_analyzed\", 0)}'); print(f'🔍 Query: {d.get(\"metadata\", {}).get(\"raw_query\", \"N/A\")[:80]}...')"
echo ""

echo "✅ Pruebas completadas"
