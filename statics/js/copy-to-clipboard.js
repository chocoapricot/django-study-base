function copyToClipboard(icon) {
    // ボタンの前の .copy-target を探してテキストを取得
    const targetText = icon.previousElementSibling.innerText;
    
    // クリップボードにコピー
    navigator.clipboard.writeText(targetText).then(() => {
        // アイコンを変更 (bi-copy -> bi-check)
        icon.classList.remove('bi-copy');
        icon.classList.add('bi-check');

        // ツールチップを動的に作成
        const tooltip = document.createElement('div');
        tooltip.className = 'copy-tooltip';
        tooltip.textContent = 'コピーしました!';
        document.body.appendChild(tooltip);

        // アイコンの位置を取得してツールチップを配置
        const rect = icon.getBoundingClientRect();
        
        // アイコンの上中央に配置 (スクロール位置考慮)
        const tooltipWidth = 100; // 仮の幅（CSSで変わるが、初期配置計算用）
        // 実際にはappend後にサイズ取得したほうが正確だが、今回はCSSで中央揃えしているので
        // leftはアイコンの中心に合わせ、CSSのtransform: translateX(-50%)で調整する
        
        tooltip.style.left = (rect.left + rect.width / 2 + window.scrollX) + 'px';
        tooltip.style.top = (rect.top + window.scrollY - 10) + 'px'; // アイコンの少し上(CSSのtop: -35pxと合わせて調整されるが、念のためJSでも制御)
        // CSSで top: -35px が当たっているので、JSではアイコンの上端基準で良い
        // ただし absolute 配置なので、 document.body 基準の座標が必要
        
        // CSSの定義を活かすため、少し修正
        // CSS: top: -35px は relative 親に対する相対だが、今回は body 直下絶対配置なので
        // offsetTop は使えない。
        // シンプルに:
        // left: rect.left + rect.width / 2 + window.scrollX
        // top: rect.top + window.scrollY
        // と設定し、CSSの transform: translateX(-50%) translateY(-100%) と margin-top で位置調整させるのが良いが、
        // 既存CSSの top: -35px を打ち消して style 属性の top が優先されるので、
        // 計算で "アイコンの35px上" を出す。
        
        tooltip.style.top = (rect.top + window.scrollY - 35) + 'px'; 
        // leftはCSSのtransform: translateX(-50%)にお任せするので、中心座標を渡す
        
        // 表示 (フェードイン)
        // appendした直後は opacity: 0
        requestAnimationFrame(() => {
            tooltip.classList.add('show');
        });

        // 2秒後に消去
        setTimeout(() => {
            tooltip.classList.remove('show');
            icon.classList.remove('bi-check');
            icon.classList.add('bi-copy');
            
            // フェードアウト完了後にDOM削除
            setTimeout(() => {
                document.body.removeChild(tooltip);
            }, 300); // transition 0.3s に合わせる
        }, 2000);

    }).catch(err => {
        console.error("コピーに失敗しました: ", err);
    });
}