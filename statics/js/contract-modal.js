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

// マスター選択関数（汎用）
window.selectMaster = function(content) {
    console.log('selectMaster called:', content);
    
    const modal = document.getElementById('masterModal');
    if (modal) {
        const targetId = modal.getAttribute('data-current-target-id');
        if (targetId) {
            const targetField = document.getElementById(targetId);
            if (targetField) {
                targetField.value = content;
            }
        }
        hideModal('masterModal');
    }
};

// 後方互換性のため
window.selectHakenMaster = window.selectMaster;

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

// マスターモーダル読み込み関数（汎用）
window.loadMasterModal = async function(selectUrl, masterType, targetId, modalTitle) {
    try {
        const modal = document.getElementById('masterModal');
        if (modal) {
            modal.querySelector('.modal-title').textContent = modalTitle;
            modal.setAttribute('data-current-target-id', targetId);
            modal.setAttribute('data-current-master-type', masterType);
            
            const url = `${selectUrl}?type=${masterType}&page=1&q=`;
            const modalBody = modal.querySelector('.modal-body');
            modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">読み込み中...</span></div></div>';
            
            await fetchModalContent(url, '#masterModal .modal-body');
            showModal('masterModal');
        }
    } catch (error) {
        console.error('Error loading master modal:', error);
    }
};

// 後方互換性のため
window.loadHakenMasterModal = window.loadMasterModal;

// マスターモーダルコンテンツ読み込み関数
window.loadMasterModalContent = async function(event, page = 1, clearSearch = false) {
    if (event) event.preventDefault();
    
    const modal = document.getElementById('masterModal');
    if (!modal) return;
    
    const modalBody = modal.querySelector('.modal-body');
    const masterType = modal.getAttribute('data-current-master-type');
    
    let url = `/common/master-select/?type=${masterType}&page=${page}`;
    
    if (!clearSearch) {
        const searchForm = document.getElementById('master-search-form');
        if (searchForm) {
            const searchQuery = searchForm.querySelector('input[name="q"]').value;
            if (searchQuery) {
                url += `&q=${encodeURIComponent(searchQuery)}`;
            }
        }
    }
    
    try {
        modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">読み込み中...</span></div></div>';
        await fetchModalContent(url, '#masterModal .modal-body');
    } catch (error) {
        console.error('Error loading master modal content:', error);
    }
};

// 後方互換性のため
window.loadHakenMasterModalContent = window.loadMasterModalContent;

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