#!/bin/bash
# Helper script for safe pre-commit workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Подготовка к коммиту...${NC}"

# Check if there are unstaged changes
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}⚠️  Обнаружены незастейдженные изменения${NC}"

    # Check if there are staged changes
    if [[ -n $(git diff --cached --name-only) ]]; then
        echo -e "${YELLOW}📝 Есть застейдженные изменения${NC}"
        echo ""
        echo -e "${BLUE}💡 Автоматически добавляем все изменения...${NC}"
        git add .
        echo -e "${GREEN}✅ Все изменения добавлены${NC}"
    else
        echo -e "${YELLOW}� Нет застейдженных изменений${NC}"
        echo -e "${BLUE}💡 Автоматически добавляем все изменения...${NC}"
        git add .
        echo -e "${GREEN}✅ Все изменения добавлены${NC}"
    fi
else
    echo -e "${GREEN}✅ Рабочая директория чиста${NC}"
fi

echo ""
echo -e "${BLUE}🔍 Запускаем pre-commit проверки...${NC}"

# Run pre-commit to see what will happen
.venv/bin/pre-commit run --all-files
PRE_COMMIT_EXIT=$?

if [ $PRE_COMMIT_EXIT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Все проверки пройдены!${NC}"
    echo -e "${GREEN}🚀 Теперь можно делать коммит${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠️  Pre-commit внес исправления${NC}"
    echo -e "${BLUE}💡 Повторно добавляем изменения...${NC}"
    git add .
    echo -e "${GREEN}✅ Исправления добавлены${NC}"
    echo ""
    echo -e "${GREEN}🚀 Теперь можно делать коммит${NC}"
fi

echo ""
echo -e "${GREEN}✅ Все проверки пройдены!${NC}"
echo -e "${GREEN}🚀 Теперь можно делать коммит${NC}"
