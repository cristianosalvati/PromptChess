#!/bin/bash

echo "=========================================="
echo "  PromptChess - Test Suite Runner"
echo "=========================================="
echo ""

REPORT_DIR="test_reports"
mkdir -p $REPORT_DIR

run_category_tests() {
    local category=$1
    local file=$2
    echo ""
    echo ">>> Esecuzione: $category"
    echo "-------------------------------------------"
    python -m pytest tests/$file -v --tb=short 2>&1 | tail -20
    echo ""
}

case "${1:-all}" in
    components)
        run_category_tests "Sezione 3 - Componenti" "test_components.py"
        ;;
    functions)
        run_category_tests "Sezione 2 - Funzionalità" "test_functions.py"
        ;;
    flow)
        run_category_tests "Sezione 5 - Flusso Operativo" "test_flow.py"
        ;;
    hallucinations)
        run_category_tests "Sezione 6 - Hallucinations" "test_hallucinations.py"
        ;;
    legacy)
        run_category_tests "Test Legacy" "test_legacy.py"
        ;;
    all)
        echo ">>> Esecuzione suite completa..."
        echo ""
        
        python -m pytest tests/ \
            -v \
            --tb=short \
            --html=$REPORT_DIR/report.html \
            --self-contained-html \
            2>&1
        
        echo ""
        echo "=========================================="
        echo "  RIEPILOGO FINALE"
        echo "=========================================="
        python -m pytest tests/ --co -q 2>/dev/null | tail -5
        echo ""
        echo "Report HTML salvato in: $REPORT_DIR/report.html"
        ;;
    summary)
        echo ">>> Riepilogo rapido (senza dettagli)..."
        python -m pytest tests/ -q --tb=no 2>&1
        ;;
    *)
        echo "Uso: ./run_tests.sh [opzione]"
        echo ""
        echo "Opzioni:"
        echo "  all           - Esegue tutti i test (default)"
        echo "  summary       - Riepilogo rapido senza dettagli"
        echo "  components    - Solo test Sezione 3 - Componenti"
        echo "  functions     - Solo test Sezione 2 - Funzionalità"
        echo "  flow          - Solo test Sezione 5 - Flusso Operativo"
        echo "  hallucinations- Solo test Sezione 6 - Hallucinations"
        echo "  legacy        - Solo test legacy (ex chess_test.py)"
        echo ""
        echo "Esempi:"
        echo "  ./run_tests.sh              # Tutti i test"
        echo "  ./run_tests.sh summary      # Solo conteggio pass/fail"
        echo "  ./run_tests.sh functions    # Solo test funzionalità"
        ;;
esac
