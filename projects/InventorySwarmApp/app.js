async function loadItems() {
  try {
    const res = await fetch('/api/items');
    const data = await res.json();
    console.log('Items loaded:', data);
  } catch(e) { console.error('Fetch error:', e); }
}
window.onload = loadItems;