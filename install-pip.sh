#!/bin/bash
# Install pip on this system

echo "🔧 Installing pip..."
echo ""

# Método 1: ensurepip
echo "Intentando: python3 -m ensurepip..."
if python3 -m ensurepip --default-pip 2>&1 | tail -3; then
    echo "✅ pip instalado"
    exit 0
fi

echo ""

# Método 2: apt-get (Linux)
if command -v apt-get &> /dev/null; then
    echo "Intentando: apt-get install python3-pip..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
    
    if python3 -m pip --version; then
        echo "✅ pip instalado"
        exit 0
    fi
fi

echo ""

# Método 3: yum (RedHat/CentOS)
if command -v yum &> /dev/null; then
    echo "Intentando: yum install python3-pip..."
    sudo yum install -y python3-pip
    
    if python3 -m pip --version; then
        echo "✅ pip instalado"
        exit 0
    fi
fi

echo ""
echo "❌ No se pudo instalar pip automáticamente"
echo ""
echo "Intenta manualmente:"
echo "  • Linux: sudo apt-get install python3-pip"
echo "  • macOS: brew install python3"
echo "  • Windows: Descarga Python 3.11+ desde python.org"
