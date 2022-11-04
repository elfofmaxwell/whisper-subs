const subText = document.getElementById("subtitleText");

// @ts-ignore
window.refresher.onUpdateSub(
    (_event: any, newSubs: string) => {
        console.log(newSubs);
        if (subText !== null && newSubs !== '') {
            subText.innerText = newSubs;
        }
    }
)
