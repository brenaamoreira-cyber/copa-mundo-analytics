# Pendências do Projeto

## des_continente vazia na tb_paises

**Status:** Pendente  
**Previsto para:** Dia 05 — DBT  
**Impacto:** Baixo — campo não é usado em nenhuma query atual  

**Descrição:**  
A coluna des_continente da tabela tb_paises está vazia para todos os países
coletados no Dia 02 via Kaggle. Apenas o Qatar (inserido manualmente no Dia 03)
tem o continente preenchido.

**Solução planejada:**  
No Dia 05, criar uma seed no DBT com o mapeamento completo
país → continente e aplicar via JOIN na camada staging.

**Países afetados:** todos exceto Qatar