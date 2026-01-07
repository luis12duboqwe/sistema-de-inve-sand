
// Script de limpieza profunda para la consola del navegador
// Copia y pega esto en la consola de desarrollador (F12 -> Console)

(async () => {
  console.log("🧹 Iniciando limpieza profunda...");
  
  // 1. Limpiar localStorage
  localStorage.clear();
  console.log("✅ localStorage limpiado");
  
  // 2. Limpiar IndexedDB (Spark KV)
  const dbs = await window.indexedDB.databases();
  for (const db of dbs) {
    if (db.name) {
      window.indexedDB.deleteDatabase(db.name);
      console.log(`✅ Base de datos eliminada: ${db.name}`);
    }
  }
  
  console.log("✨ Limpieza completada. Recargando...");
  setTimeout(() => window.location.reload(), 1000);
})();
