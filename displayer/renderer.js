"use strict";
const subText = document.getElementById("subtitleText");
// @ts-ignore
window.refresher.onUpdateSub((_event, newSubs) => {
    console.log(newSubs);
    if (subText !== null && newSubs !== '') {
        subText.innerText = newSubs;
    }
});
