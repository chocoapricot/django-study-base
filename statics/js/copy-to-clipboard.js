function copyToClipboard(button) {
    // ボタンの前の .copy-target を探してテキストを取得
    const targetText = button.previousElementSibling.innerText;
    navigator.clipboard.writeText(targetText).then(() => {
        // コピーが成功したらメッセージを表示
        const copyMessage = button.nextElementSibling;
        copyMessage.style.display = "inline";

        // 2秒後にメッセージを非表示にする
        setTimeout(() => {
            copyMessage.style.display = "none";
        }, 1000);
    }).catch(err => {
        console.error("コピーに失敗しました: ", err);
    });
}