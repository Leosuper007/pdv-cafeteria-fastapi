@echo off
chcp 65001 > nul
title Cafeteria Grão — Resetar Cardápio

echo.
echo  ============================================
echo    CAFETERIA GRAO - ATUALIZAR CARDAPIO
echo  ============================================
echo.

python resetar_produtos.py

echo.
pause
