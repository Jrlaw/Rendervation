// The houses page (houses/index.html): each room's card shows its chosen design's picture
// (web/cards/<id>.jpg), from the server (GET /api/rooms). Opened from disk, the page's own pictures stay.
(async function () {
  if (location.protocol === "file:") return;
  let rooms;
  try { rooms = await (await fetch("/api/rooms")).json(); } catch (err) { console.error(err); return; }
  rooms.forEach(({ room, card }) => {
    if (!card) return;
    const rel = room.split("/").slice(1).join("/");   // houses/ours/rooms/office -> ours/rooms/office
    const link = document.querySelector(`article.room a[href="${rel}/web/index.html"]`);
    const img = link && link.closest("article.room").querySelector("img");
    if (img) img.src = card;
  });
})();
