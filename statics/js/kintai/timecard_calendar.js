/**
 * TimecardCalendar
 * 勤怠カレンダー入力画面の共通ロジック
 */
class TimecardCalendar {
    constructor(options) {
        this.options = Object.assign({
            defaultStartTime: '',
            defaultEndTime: '',
            defaultBreakMinutes: '60',
            // コールバック
            onFillAll: null, // 一括入力時の追加処理（契約選択など）
        }, options);

        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeFields();
    }

    bindEvents() {
        // フォーム送信時のバリデーション
        const form = document.getElementById('calendar-form');
        if (form) {
            form.addEventListener('submit', (e) => this.validateForm(e));
        }

        // 勤務区分の変更イベント
        document.querySelectorAll('.work-type-select').forEach(select => {
            select.addEventListener('change', (e) => {
                const day = e.target.dataset.day;
                this.toggleFields(day);
            });
        });

        // 就業時間プルダウンの変更イベント
        document.querySelectorAll('.work-time-select').forEach(select => {
            select.addEventListener('change', (e) => this.handleWorkTimeChange(e.target));
        });

        // 一括保存ボタン（契約通り）
        const fillBtn = document.getElementById('fill-all-btn');
        if (fillBtn) {
            fillBtn.addEventListener('click', () => this.fillAll());
        }

        // クリアボタン
        const clearBtn = document.getElementById('clear-all-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearAll());
        }
    }

    initializeFields() {
        // 全ての行に対して初期表示状態を設定
        document.querySelectorAll('.work-type-select').forEach(select => {
            const day = select.dataset.day;
            this.toggleFields(day);
        });
    }

    // 勤務区分の変更に応じて入力欄の表示/非表示を切り替え
    toggleFields(day) {
        const row = document.querySelector(`tr[data-day="${day}"]`);
        if (!row) return;

        const workType = row.querySelector('.work-type-select').value;
        const startTime = row.querySelector('.start-time');
        const endTime = row.querySelector('.end-time');
        const breakMinutes = row.querySelector('.break-minutes');
        const paidLeave = row.querySelector('.paid-leave');
        
        if (workType === '10') {  // 出勤
            startTime.disabled = false;
            endTime.disabled = false;
            breakMinutes.disabled = false;
            paidLeave.disabled = true;
            paidLeave.value = 0;
        } else if (workType === '40') {  // 有給休暇
            startTime.disabled = true;
            endTime.disabled = true;
            breakMinutes.disabled = true;
            paidLeave.disabled = false;
            startTime.value = '';
            endTime.value = '';
            breakMinutes.value = 0;
        } else {  // その他
            startTime.disabled = true;
            endTime.disabled = true;
            breakMinutes.disabled = true;
            paidLeave.disabled = true;
            startTime.value = '';
            endTime.value = '';
            breakMinutes.value = 0;
            paidLeave.value = 0;
        }
    }

    // 就業時間プルダウン選択時の処理
    handleWorkTimeChange(select) {
        const day = select.dataset.day;
        const selectedOption = select.options[select.selectedIndex];
        
        if (selectedOption.value) {
            const row = document.querySelector(`tr[data-day="${day}"]`);
            
            // 勤務区分を「出勤」に設定
            row.querySelector('.work-type-select').value = '10';
            
            // 時刻を設定
            row.querySelector('.start-time').value = selectedOption.dataset.startTime || '';
            row.querySelector('.end-time').value = selectedOption.dataset.endTime || '';
            
            // 翌日フラグを設定
            const startNext = row.querySelector('.start-time-next-day');
            const endNext = row.querySelector('.end-time-next-day');
            if (startNext) startNext.checked = selectedOption.dataset.startNextDay === 'true';
            if (endNext) endNext.checked = selectedOption.dataset.endNextDay === 'true';
            
            // 休憩時間を設定
            row.querySelector('.break-minutes').value = selectedOption.dataset.breakMinutes || '0';
            
            // 入力欄を有効化
            this.toggleFields(day);
        }
    }

    // 一括入力（契約通り）
    fillAll() {
        if (!confirm('平日に対して契約の就業時間で一括設定しますか？' + (this.options.onFillAll ? '\n※最初の有効な契約が自動選択されます。' : ''))) return;
        
        document.querySelectorAll('tr[data-day]').forEach(row => {
            const day = row.dataset.day;
            const dateText = row.querySelector('td:nth-child(1)').textContent.trim();
            const weekdayName = dateText.match(/\((.)\)/)[1];
            const isHoliday = row.dataset.isHoliday === 'true';
            
            // カスタム処理（契約選択など）
            if (typeof this.options.onFillAll === 'function') {
                this.options.onFillAll(row);
            }
            
            // 土日祝日
            if (weekdayName === '土' || weekdayName === '日' || isHoliday) {
                row.querySelector('.work-type-select').value = '70'; // 稼働無し
                row.querySelector('.start-time').value = '';
                row.querySelector('.end-time').value = '';
                row.querySelector('.break-minutes').value = '0';
                row.querySelector('.paid-leave').value = '0';
                this.toggleFields(day);
            } else {
                // 平日
                row.querySelector('.work-type-select').value = '10'; // 出勤
                row.querySelector('.start-time').value = this.options.defaultStartTime;
                row.querySelector('.end-time').value = this.options.defaultEndTime;
                row.querySelector('.break-minutes').value = this.options.defaultBreakMinutes;
                row.querySelector('.paid-leave').value = '0';
                this.toggleFields(day);
            }
        });
    }

    // 全てクリア
    clearAll() {
        if (!confirm('全ての入力をクリアしますか？')) return;
        
        document.querySelectorAll('tr[data-day]').forEach(row => {
            const day = row.dataset.day;
            
            // 契約選択があればクリア
            const contractSelect = row.querySelector('.contract-select');
            if (contractSelect) contractSelect.value = '';

            // 就業時間選択があればクリア
            const workTimeSelect = row.querySelector('.work-time-select');
            if (workTimeSelect) {
                workTimeSelect.value = '';
                // 契約選択がある場合（staff_timecard_calendar）、契約未選択時はdisabledにする必要があるが
                // ここでは単純に値をクリアする。disabled制御は別途契約選択のchangeイベント等で制御されるべきだが
                // clearAllで契約もクリアされるなら、disabledにすべきか？
                // staff_timecard_calendar.htmlのロジックでは、契約選択のchangeイベントで制御している。
                // ここで値をクリアした後、契約選択のchangeイベントを発火させるか、
                // あるいは updateWorkTimeOptions を呼ぶ必要がある。
                // 汎用的にするために、changeイベントを発火させるのが良さそう。
            }

            row.querySelector('.work-type-select').value = '';
            row.querySelector('.start-time').value = '';
            row.querySelector('.end-time').value = '';
            row.querySelector('.break-minutes').value = '0';
            row.querySelector('.paid-leave').value = '0';
            
            // 翌日チェックボックスもクリア
            const startNextDay = row.querySelector('.start-time-next-day');
            const endNextDay = row.querySelector('.end-time-next-day');
            if (startNextDay) startNextDay.checked = false;
            if (endNextDay) endNextDay.checked = false;
            
            this.toggleFields(day);

            // 契約選択のchangeイベントを発火させて、依存するUI（就業時間プルダウンなど）を更新
            if (contractSelect) {
                contractSelect.dispatchEvent(new Event('change'));
            }
        });
    }

    // バリデーション
    validateForm(e) {
        let hasError = false;
        let errorMessages = [];
        
        document.querySelectorAll('tr[data-day]').forEach(row => {
            const day = row.dataset.day;
            const workType = row.querySelector('.work-type-select').value;
            const startTime = row.querySelector('.start-time').value;
            const endTime = row.querySelector('.end-time').value;
            
            // エラー表示をクリア
            row.style.backgroundColor = '';

            if (workType === '10') { // 出勤
                if (!startTime || !endTime) {
                    hasError = true;
                    errorMessages.push(`${day}日: 出勤の場合は出勤・退勤時刻を入力してください。`);
                    row.style.backgroundColor = '#fff3cd'; // 警告色
                } else if (startTime >= endTime) {
                    // 翌日フラグのチェック
                    const startNext = row.querySelector('.start-time-next-day').checked;
                    const endNext = row.querySelector('.end-time-next-day').checked;
                    
                    if (!startNext && !endNext) {
                        hasError = true;
                        errorMessages.push(`${day}日: 退勤時刻は出勤時刻より後の時刻を入力してください。`);
                        row.style.backgroundColor = '#fff3cd';
                    }
                }
            }
        });
        
        if (hasError) {
            e.preventDefault();
            alert('入力エラーがあります。\n\n' + errorMessages.slice(0, 5).join('\n') + (errorMessages.length > 5 ? '\n...' : ''));
        }
    }
}
