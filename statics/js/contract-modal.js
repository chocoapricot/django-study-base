/**
 * 契約フォーム用モーダル共通JavaScript
 */

// グローバル関数を即座に定義（IIFEを使わずに直接定義）

// 基本的なユーティリティ関数
function showModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (modalElement && typeof bootstrap !== 'undefined') {
        let modal = bootstrap.Modal.getInstance(modalElement);
        if (!modal) {
            modal = new bootstrap.Modal(modalElement, {
                backdrop: true,
                keyboard: true,
                focus: true
            });
        }
        modal.show();
    }
}

function hideModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (modalElement && typeof bootstrap !== 'undefined') {
        // フォーカスされている要素があれば、フォーカスを外す
        const focusedElement = modalElement.querySelector(':focus');
        if (focusedElement) {
            focusedElement.blur();
        }

        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    }
}

async function fetchModalContent(url, modalSelector) {
    try {
        const response = await fetch(url);
        const html = await response.text();
        const modalBody = document.querySelector(modalSelector);
        if (modalBody) {
            modalBody.innerHTML = html;
        }
        return html;
    } catch (error) {
        console.error('Modal content fetch error:', error);
        const modalBody = document.querySelector(modalSelector);
        if (modalBody) {
            modalBody.innerHTML = '<p class="text-center text-danger">データの取得に失敗しました。</p>';
        }
        throw error;
    }
}

// スタッフ選択関数
window.selectStaff = function(staffId, staffName, employmentType, employmentTypeName, badgeClass) {
    console.log('selectStaff called:', staffId, staffName);

    // フィールドに値を設定
    const staffField = document.querySelector('input[name="staff"]');
    if (staffField) {
        staffField.value = staffId;
    }

    // 雇用形態フィールドに値を設定
    const employmentTypeField = document.querySelector('input[name="employment_type"]');
    if (employmentTypeField && employmentType) {
        employmentTypeField.value = employmentType;
    }

    // 表示テキストを更新
    const displayText = document.getElementById('staff-display-text');
    if (displayText) {
        displayText.textContent = staffName;
    }

    // 雇用形態バッジを更新
    const badgeElement = document.getElementById('staff-employment-type-badge');
    if (badgeElement && employmentType && employmentTypeName) {
        const className = badgeClass || 'bg-primary';
        badgeElement.innerHTML = `<span class="badge ${className}" style="font-size:13px">${employmentTypeName}</span>`;

        // 契約書パターンを更新（存在する場合）
        if (typeof updateContractPatterns === 'function') {
            updateContractPatterns(employmentType);
        }
    } else if (badgeElement) {
        badgeElement.textContent = '-';
        if (typeof updateContractPatterns === 'function') {
            updateContractPatterns(null);
        }
    }

    // モーダルを閉じる
    hideModal('selectModal');
};

// クライアント選択関数
window.selectClient = function(clientId, clientName) {
    console.log('selectClient called:', clientId, clientName);

    // フィールドに値を設定
    const clientField = document.querySelector('input[name="client"]');
    if (clientField) {
        clientField.value = clientId;
    }

    // 表示テキストを更新
    const displayText = document.getElementById('client-display-text');
    if (displayText) {
        displayText.textContent = clientName;
    }

    // モーダルを閉じる
    hideModal('selectModal');

    // 派遣契約の場合、関連フィールドを更新
    const contractTypeField = document.querySelector('select[name="client_contract_type_code"]');
    if (contractTypeField && contractTypeField.value === '20' && typeof updateDispatchFields === 'function') {
        updateDispatchFields(clientId);
        // 就業場所をクリア
        const workLocationField = document.querySelector('textarea[name="work_location"]');
        if (workLocationField) {
            workLocationField.value = '';
        }
    }
};

// 派遣マスター選択関数
window.selectHakenMaster = function(content) {
    console.log('selectHakenMaster called:', content);

    const modal = document.getElementById('hakenMasterModal');
    if (modal) {
        const targetId = modal.getAttribute('data-current-target-id');
        if (targetId) {
            const targetField = document.getElementById(targetId);
            if (targetField) {
                targetField.value = content;
            }
        }
        hideModal('hakenMasterModal');
    }
};

// スタッフモーダル読み込み関数
window.loadStaffModal = async function(selectUrl) {
    try {
        const url = `${selectUrl}?from_modal=1`;
        await fetchModalContent(url, '#selectModal .modal-body');
        showModal('selectModal');
    } catch (error) {
        alert('取得失敗: ' + error);
    }
};

// クライアントモーダル読み込み関数
window.loadClientModal = async function(selectUrl, contractTypeCode) {
    try {
        const url = `${selectUrl}?from_modal=1&client_contract_type_code=${contractTypeCode || ''}`;
        await fetchModalContent(url, '#selectModal .modal-body');
        showModal('selectModal');
    } catch (error) {
        alert('取得失敗: ' + error);
    }
};

// 派遣マスターモーダル読み込み関数
window.loadHakenMasterModal = async function(selectUrl, masterType, targetId, modalTitle) {
    try {
        const modal = document.getElementById('hakenMasterModal');
        if (modal) {
            modal.querySelector('.modal-title').textContent = modalTitle;
            modal.setAttribute('data-current-target-id', targetId);
            modal.setAttribute('data-current-master-type', masterType);

            const url = `${selectUrl}?type=${masterType}&page=1&q=`;
            const modalBody = modal.querySelector('.modal-body');
            modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">読み込み中...</span></div></div>';

            await fetchModalContent(url, '#hakenMasterModal .modal-body');
            showModal('hakenMasterModal');
        }
    } catch (error) {
        console.error('Error loading haken master modal:', error);
    }
};

// モーダルが閉じられる際のフォーカス管理
document.addEventListener('DOMContentLoaded', function() {
    // すべてのモーダルに対してイベントリスナーを設定
    const modals = document.querySelectorAll('.modal');
    modals.forEach(function(modal) {
        modal.addEventListener('hide.bs.modal', function() {
            // モーダル内のフォーカスされている要素からフォーカスを外す
            const focusedElement = modal.querySelector(':focus');
            if (focusedElement) {
                focusedElement.blur();
            }
        });
    });
});

console.log('Contract modal functions loaded');