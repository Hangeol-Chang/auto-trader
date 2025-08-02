// inputFields.js - Web Components 기반 Input Field 컴포넌트

// 공통 스타일 정의
const componentStyles = `
    /* Input Field 컴포넌트 스타일 */
    .input-group {
        display: flex;
        margin-bottom: 16px;
        gap: 6px;
        position: relative;
        flex-grow: 1;
        align-items: stretch;
    }

    .input-label {
        font-size: 12px;
        font-weight: 500;
        color: #e0e0e0;
        margin-bottom: 4px;
        position: absolute;
        top: -5px;
        left: 8px;
    }

    .input-field, .select-field {
        padding: 10px 12px;
        border: 2px solid #444;
        border-radius: 6px;
        background-color: #222;
        color: white;
        font-size: 14px;
        transition: all 0.3s ease;
        outline: none;
        min-width: 80px;
        width: auto;
    }

    .input-field:focus, .select-field:focus {
        border-color: #007acc;
        box-shadow: 0 0 0 3px rgba(0, 122, 204, 0.1);
        background-color: #2a2a2a;
    }

    .input-field::placeholder {
        color: #888;
    }

    .date-input {
        font-family: 'Courier New', monospace;
        letter-spacing: 1px;
    }

    .search-container {
        display: flex;
        gap: 8px;
        align-items: stretch;
    }

    .search-input {
        flex: 1;
    }

    .btn {
        padding: 10px 16px;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        outline: none;
    }

    .btn-primary {
        background-color: #007acc;
        color: white;
    }

    .btn-primary:hover {
        background-color: #005a9e;
        transform: translateY(-1px);
    }

    .btn-search {
        background-color: #28a745;
        color: white;
        padding: 10px 12px;
        min-width: 44px;
    }

    .btn-search:hover {
        background-color: #218838;
    }

    .btn:active {
        transform: translateY(0);
    }

    .field-group {
        display: flex;
        flex-direction: row;
        gap: 4px;
        margin-bottom: 10px;
        justify-content: space-between;
        max-width: 100%;
    }

    .divider {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, #444, transparent);
        margin: 20px 0;
    }

    /* 반응형 스타일 */
    @media (max-width: 320px) {
        .field-group.horizontal {
            flex-direction: column;
            // align-items: stretch;
        }
        
        .search-container {
            flex-direction: column;
        }
        
        .btn {
            width: 100%;
        }
    }
`;

// 전역 스타일 주입 함수
function injectGlobalStyles() {
    if (document.getElementById('inputfield-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'inputfield-styles';
    style.textContent = componentStyles;
    document.head.appendChild(style);
}

// 텍스트 입력 컴포넌트
class TextInput extends HTMLElement {
    connectedCallback() {
        const label = this.getAttribute('label') || '';
        const placeholder = this.getAttribute('placeholder') || '';
        const value = this.getAttribute('value') || '';
        const type = this.getAttribute('type') || 'text';
        const id = this.getAttribute('input-id') || '';
        
        this.innerHTML = `
            <div class="input-group">
                <label for="${id}" class="input-label">${label}</label>
                <input 
                    type="${type}" 
                    id="${id}" 
                    class="input-field ${type === 'date' ? 'date-input' : ''}" 
                    placeholder="${placeholder}" 
                    value="${value}"
                    ${type === 'date' ? 'maxlength="8"' : ''}
                />
            </div>
        `;
    }
}

// 셀렉트 컴포넌트
class SelectInput extends HTMLElement {
    connectedCallback() {
        const label = this.getAttribute('label') || '';
        const id = this.getAttribute('input-id') || '';
        const value = this.getAttribute('value') || '';
        
        // options는 slot으로 처리하거나 attribute로 JSON 전달
        const optionsData = this.getAttribute('options');
        let optionsHtml = '';
        
        if (optionsData) {
            const options = JSON.parse(optionsData);
            optionsHtml = options.map(option => 
                `<option value="${option.value}" ${option.value === value ? 'selected' : ''}>${option.text}</option>`
            ).join('');
        }
        
        this.innerHTML = `
            <div class="input-group">
                <label for="${id}" class="input-label">${label}</label>
                <select id="${id}" class="select-field">
                    ${optionsHtml}
                </select>
            </div>
        `;
    }
}

// 검색 입력 컴포넌트
class SearchInput extends HTMLElement {
    connectedCallback() {
        const label = this.getAttribute('label') || '';
        const placeholder = this.getAttribute('placeholder') || '';
        const value = this.getAttribute('value') || '';
        const inputId = this.getAttribute('input-id') || '';
        const btnId = this.getAttribute('btn-id') || '';
        const onSearch = this.getAttribute('on-search') || '';
        
        this.innerHTML = `
            <div class="input-group">
                <label for="${inputId}" class="input-label">${label}</label>
                <div class="search-container">
                    <input 
                        type="text" 
                        id="${inputId}" 
                        class="input-field search-input" 
                        placeholder="${placeholder}" 
                        value="${value}"
                    />
                    <button 
                        id="${btnId}" 
                        class="btn btn-search" 
                        ${onSearch ? `onclick="${onSearch}"` : ''}
                    >
                        🔍
                    </button>
                </div>
            </div>
        `;
    }
}

// 버튼 컴포넌트
class ButtonComponent extends HTMLElement {
    connectedCallback() {
        const text = this.getAttribute('text') || 'Button';
        const id = this.getAttribute('btn-id') || '';
        const onClick = this.getAttribute('on-click') || '';
        const className = this.getAttribute('btn-class') || 'btn-primary';
        
        this.innerHTML = `
            <button 
                id="${id}" 
                class="btn ${className}" 
                ${onClick ? `onclick="${onClick}"` : ''}
            >
                ${text}
            </button>
        `;
    }
}

// 필드 그룹 컴포넌트
class FieldGroup extends HTMLElement {
    connectedCallback() {
        const direction = this.getAttribute('direction') || 'horizontal';
        const className = direction === 'vertical' ? 'field-group vertical' : 'field-group';
        
        this.classList.add(className);
    }
}

// 구분선 컴포넌트
class DividerComponent extends HTMLElement {
    connectedCallback() {
        this.innerHTML = '<hr class="divider">';
    }
}

// 컴포넌트 등록
customElements.define('text-input', TextInput);
customElements.define('select-input', SelectInput);
customElements.define('search-input', SearchInput);
customElements.define('button-component', ButtonComponent);
customElements.define('field-group', FieldGroup);
customElements.define('divider-component', DividerComponent);

// 스타일 자동 주입 (스크립트 로드 시)
document.addEventListener('DOMContentLoaded', () => {
    injectGlobalStyles();
});
