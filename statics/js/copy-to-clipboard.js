function copyToClipboard(icon) {
    // ボタンの前の .copy-target を探してテキストを取得
    const targetText = icon.previousElementSibling.innerText;
    navigator.clipboard.writeText(targetText).then(() => {
        // コピーが成功したらメッセージを表示
        const copyMessage = icon.nextElementSibling;
        copyMessage.style.display = "inline";

        // アイコンを変更 (bi-copy -> bi-check)
        icon.classList.remove('bi-copy');
        icon.classList.add('bi-check');

        // 2秒後にメッセージを非表示にし、アイコンを元に戻す
        setTimeout(() => {
            copyMessage.style.display = "none";
            icon.classList.remove('bi-check');
            icon.classList.add('bi-copy');
        }, 2000);
    }).catch(err => {
        console.error("コピーに失敗しました: ", err);
    });
}