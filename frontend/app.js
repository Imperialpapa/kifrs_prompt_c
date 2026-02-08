/**
 * [Frontend Application Logic]
 * Alpine.js를 사용한 단일 페이지 애플리케이션(SPA) 구조
 */
function app() {
    return {
        // =================================================================
        // 1. Core State & Configuration
        // =================================================================
        API_BASE_URL: window.location.origin, // 호스트 자동 감지
        sidebarOpen: false,
        currentTab: 'upload', 
        
        fileA: null, 
        fileB: null, 
        dragOverA: false,
        dragOverB: false,
        isLoading: false,
        useSavedRule: true,
        selectedSavedRuleId: null,

        results: null, 
        dbErrors: null,
        searchQuery: '',
        filterSheet: 'all',
        currentPage: 1,
        pageSize: 20,
        frontendVersion: 'v1.4.7',
        backendVersion: 'Checking...',
        selectedSheet: null,
        selectedRuleDetailId: null,
        
        // 시트 선택 변경
        selectSheet(sheetName) {
            this.selectedSheet = sheetName;
            this.selectedRuleDetailId = null;
            this.$nextTick(() => {
                this.renderCharts();
            });
        },

        chartInstance: null,
        dashboardTab: 'analysis', 

        // Fix State
        fixActiveTab: 'before',
        fixFilterSheet: 'all',
        fixPreviewFilter: 'all',
        selectedFixItems: [],
        isDownloading: false,
        fixPreview: { total: 0, success: 0, fail: 0, successRate: 0, items: [] },

        // Feedback State
        feedbackModalOpen: false,
        selectedError: null,
        feedbackReason: '',

        // Rules Management State
        ruleFiles: [],
        selectedRuleFile: null,
        ruleFileDetails: null,
        uploadingRuleFile: false,
        ruleFileToUpload: null,
        ruleFileVersion: '1.0',
        ruleFileUploadedBy: 'system',
        ruleFileNotes: '',

        // Settings State
        settingsModalOpen: false,
        aiProvider: 'openai',

        // Rule Editor State
        editingRule: null,
        editingRuleParamsJson: '{}',
        paramsValid: true,

        // Rule Mapping State
        ruleMappings: null,
        ruleMappingsLoading: false,
        selectedMappingSheet: 'all',
        mappingFilterStatus: 'all',
        editingMapping: null,
        reinterpretingRule: false,
        ruleManagementStep: 1,

        // Create Rule State
        createRuleModalOpen: false,
        newRule: {
            sheet_name: 'Common',
            custom_sheet_name: '',
            column_name: '',
            rule_text: '',
            condition: '',
            ai_rule_type: 'required',
            is_common: true
        },

        // AI Smart Analysis State
        smartAnalysisTab: 'cross_field',
        smartAnalysisLoading: false,
        crossFieldResults: null,
        dataProfileResults: null,
        smartAnalysisFileA: null,
        crossFieldSeverityFilter: 'all',
        profileCategoryFilter: 'all',

        toasts: [],

        // =================================================================
        // 6. Navigation Groups (메뉴 정의)
        // =================================================================
        navGroups: [
            {
                title: "검증 실행",
                items: [
                    { id: 'upload', label: '파일 업로드 (검증)', icon: 'ph-upload-simple' }
                ]
            },
            {
                title: "결과 분석 및 수정",
                items: [
                    { id: 'fix', label: '오류 항목 수정하기', icon: 'ph-wrench' },
                    { id: 'ai_fix', label: 'AI 스마트 수정', icon: 'ph-magic-wand' }
                ]
            },
            {
                title: "시스템 관리",
                items: [
                    { id: 'learning', label: 'AI 학습 현황', icon: 'ph-brain' },
                    { id: 'statistics', label: '통계 분석', icon: 'ph-trend-up' },
                    { id: 'settings', label: '설정 (AI 모델)', icon: 'ph-gear' },
                    { id: 'rules', label: '규칙 관리', icon: 'ph-gear-six' }
                ]
            },
            {
                title: "참고 기능",
                items: [
                    { id: 'reference', label: '참고 자료', icon: 'ph-article' },
                    { id: 'report', label: '상세 리포트', icon: 'ph-table' }
                ]
            }
        ],

        get navItems() {
            return this.navGroups.flatMap(g => g.items);
        },

        // =================================================================
        // Actions & Methods
        // =================================================================

        async init() {
            console.log("App Initializing...");
            try {
                const res = await fetch(`${this.API_BASE_URL}/version`);
                if (res.ok) {
                    const data = await res.json();
                    this.backendVersion = `Back: v${data.system_version}`;
                }
            } catch (e) {
                this.backendVersion = "Back: Offline";
            }
            await this.loadRuleFiles();
        },

        resetResults() {
            this.results = null;
            this.dbErrors = null;
            this.selectedSheet = null;
            this.selectedRuleDetailId = null;
            this.fixSuggestions = [];
            this.selectedFixes = [];
            this.fixPreview = { total: 0, success: 0, fail: 0, successRate: 0, items: [] };
            this.selectedFixItems = [];
            this.searchQuery = '';
            
            if (this.chartInstance) {
                this.chartInstance.destroy();
                this.chartInstance = null;
            }
        },

        handleFileSelect(event, type) {
            const file = event.target.files[0];
            if (file) {
                if (type === 'A') {
                    this.resetResults();
                    this.fileA = file;
                    this.autoStartValidation();
                }
                if (type === 'B') this.fileB = file;
            }
        },

        handleDrop(event, type) {
            this[type === 'A' ? 'dragOverA' : 'dragOverB'] = false;
            const file = event.dataTransfer.files[0];
            if (file) {
                if (type === 'A') {
                    this.resetResults();
                    this.fileA = file;
                    this.autoStartValidation();
                }
                if (type === 'B') this.fileB = file;
            }
        },

        autoStartValidation() {
            if (this.selectedSavedRuleId && !this.isLoading) {
                setTimeout(() => this.validateFiles(), 100);
            }
        },

        async loadRuleFiles() {
            try {
                const response = await fetch(`${this.API_BASE_URL}/rules/files?status=active&limit=50`);
                if (!response.ok) return;
                const data = await response.json();
                const fileMap = new Map();
                for (const file of data) {
                    const key = `${file.file_name}_${file.file_version}`;
                    const existing = fileMap.get(key);
                    if (!existing || new Date(file.uploaded_at) > new Date(existing.uploaded_at)) {
                        fileMap.set(key, file);
                    }
                }
                this.ruleFiles = Array.from(fileMap.values()).sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at));
                if (!this.selectedSavedRuleId && this.ruleFiles.length > 0) {
                    this.selectedSavedRuleId = this.ruleFiles[0].id;
                }
            } catch (e) { console.error(e); }
        },

        async validateFiles() {
            if (!this.fileA || !this.selectedSavedRuleId) return;
            this.resetResults();
            this.isLoading = true;
            const formData = new FormData();
            formData.append('employee_file', this.fileA);
            try {
                const url = `${this.API_BASE_URL}/validate-with-db-rules?rule_file_id=${this.selectedSavedRuleId}`;
                const response = await fetch(url, { method: 'POST', body: formData });
                if (!response.ok) throw new Error('Validation Failed');
                const data = await response.json();

                const sessionRes = await fetch(`${this.API_BASE_URL}/sessions/${data.session_id}`);
                const sessionData = await sessionRes.json();
                const fullResults = sessionData.session.full_results;
                
                if (fullResults) {
                    this.results = { 
                        ...fullResults, 
                        metadata: { ...fullResults.metadata, session_id: data.session_id } 
                    };
                    
                    if (this.results.metadata) {
                        const order = this.results.metadata.sheet_order || [];
                        const summarySheets = Object.keys(this.results.metadata.sheets_summary || {});
                        this.selectedSheet = order[0] || summarySheets[0] || null;
                    }
                }
                
                this.currentTab = 'fix';
                this.$nextTick(() => this.renderCharts());
            } catch (error) {
                alert('오류: ' + error.message);
            } finally {
                this.isLoading = false;
            }
        },

        // Rule Management
        handleRuleFileSelect(event) {
            const file = event.target.files[0];
            if (file) this.ruleFileToUpload = file;
        },

        async uploadRuleFileToDb() {
            if (!this.ruleFileToUpload) return;
            this.uploadingRuleFile = true;
            try {
                const formData = new FormData();
                formData.append('rules_file', this.ruleFileToUpload);
                formData.append('file_version', this.ruleFileVersion);
                formData.append('uploaded_by', this.ruleFileUploadedBy);
                if (this.ruleFileNotes) formData.append('notes', this.ruleFileNotes);

                const response = await fetch(`${this.API_BASE_URL}/rules/upload-to-db`, { method: 'POST', body: formData });
                if (!response.ok) throw new Error('업로드 실패');
                const result = await response.json();
                this.showToast(`업로드 완료: v${result.file_version}`, 'success');
                this.ruleFileToUpload = null;
                await this.loadRuleFiles();
                if (result.id) {
                    this.selectedSavedRuleId = result.id;
                    this.selectedRuleFile = result.id;
                    await this.goToMappingReview();
                }
            } catch (e) { this.showToast(e.message, 'error'); } 
            finally { this.uploadingRuleFile = false; }
        },

        async viewRuleFileDetails(fileId) {
            try {
                const response = await fetch(`${this.API_BASE_URL}/rules/files/${fileId}`);
                if (response.ok) {
                    this.ruleFileDetails = await response.json();
                    this.selectedRuleFile = fileId;
                    this.currentTab = 'rule_detail';
                }
            } catch (e) { console.error(e); }
        },

        closeRuleFileDetails() {
            this.ruleFileDetails = null;
            this.selectedRuleFile = null;
            this.currentTab = 'rules';
        },

        async archiveRuleFile(fileId) {
            if (!confirm('이 규칙 파일을 삭제하시겠습니까?\n\n모든 관련 규칙이 비활성화됩니다.')) {
                return;
            }
            try {
                const response = await fetch(`${this.API_BASE_URL}/rules/files/${fileId}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail?.message || '삭제 실패');
                }

                this.showToast('규칙 파일이 삭제되었습니다.', 'success');
                
                // 목록 새로고침
                await this.loadRuleFiles();
                
                // 상세 페이지가 열려있으면 닫기
                if (this.ruleFileDetails && this.ruleFileDetails.id === fileId) {
                    this.closeRuleFileDetails();
                }
            } catch (e) {
                this.showToast(e.message, 'error');
            }
        },

        async downloadRuleFile(fileId, fileName) {
            try {
                const response = await fetch(`${this.API_BASE_URL}/rules/download/${fileId}`);
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = fileName || 'rules.xlsx';
                document.body.appendChild(a); a.click(); document.body.removeChild(a);
            } catch (e) { alert(e.message); }
        },

        async reinterpretRules(fileId) {
            if (!confirm('규칙을 재해석하시겠습니까?')) return;
            try {
                this.showToast('규칙 재해석 중...', 'info');
                const response = await fetch(`${this.API_BASE_URL}/rules/reinterpret/${fileId}?use_local_parser=true`, { method: 'POST' });
                if (response.ok) {
                    const result = await response.json();
                    this.showToast(`재해석 완료: ${result.interpreted_rules}개`, 'success');
                    await this.loadRuleFiles();
                }
            } catch (e) { alert(e.message); }
        },

        async goToMappingReview() {
            if (!this.selectedRuleFile) return;
            this.ruleManagementStep = 2;
            await this.loadRuleMappings(this.selectedRuleFile);
            await this.viewRuleFileDetails(this.selectedRuleFile);
        },

        async loadRuleMappings(fileId) {
            this.ruleMappingsLoading = true;
            try {
                const response = await fetch(`${this.API_BASE_URL}/rules/files/${fileId}/mappings`);
                if (response.ok) this.ruleMappings = await response.json();
            } catch (e) { this.showToast('매핑 로딩 실패', 'error'); }
            finally { this.ruleMappingsLoading = false; }
        },

        // AI Learning Statistics
        async loadLearningStats() {
            try {
                console.log("Loading Learning Statistics...");
                const response = await fetch(`${this.API_BASE_URL}/learning/statistics`);
                if (!response.ok) throw new Error('학습 통계 로딩 실패');
                this.learningStats = await response.json();

                this.$nextTick(() => {
                    this.renderLearningCharts();
                });
            } catch (e) {
                console.error('Learning stats error:', e);
                this.showToast('학습 통계를 불러오는데 실패했습니다.', 'error');
            }
        },

        renderLearningCharts() {
            if (!this.learningStats) return;

            // 1. 학습 추이 차트 (Line)
            const trendCtx = document.getElementById('learningTrendChart');
            if (trendCtx && this.learningStats.daily_learning_trend) {
                const trend = this.learningStats.daily_learning_trend;
                new Chart(trendCtx, {
                    type: 'line',
                    data: {
                        labels: trend.map(d => d.date.slice(5)),
                        datasets: [
                            {
                                label: '총 패턴 수',
                                data: trend.map(d => d.total_patterns),
                                borderColor: '#8b5cf6',
                                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                                tension: 0.3,
                                fill: true
                            }
                        ]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });
            }

            // 2. 패턴 유형 분포 차트 (Doughnut)
            const typeCtx = document.getElementById('patternTypeChart');
            if (typeCtx && this.learningStats.pattern_type_distribution) {
                const dist = this.learningStats.pattern_type_distribution;
                new Chart(typeCtx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(dist),
                        datasets: [{
                            data: Object.values(dist),
                            backgroundColor: ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'],
                            borderWidth: 0
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false, cutout: '60%' }
                });
            }

            // 3. 신뢰도 분포 차트 (Bar)
            const confCtx = document.getElementById('confidenceDistChart');
            if (confCtx && this.learningStats.confidence_distribution) {
                const dist = this.learningStats.confidence_distribution;
                new Chart(confCtx, {
                    type: 'bar',
                    data: {
                        labels: Object.keys(dist),
                        datasets: [{
                            label: '패턴 수',
                            data: Object.values(dist),
                            backgroundColor: '#8b5cf6',
                            borderRadius: 4
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });
            }

            // 4. 성공률 추이 차트 (Line)
            const successCtx = document.getElementById('successRateChart');
            if (successCtx && this.learningStats.weekly_success_rate) {
                const weekly = this.learningStats.weekly_success_rate;
                new Chart(successCtx, {
                    type: 'line',
                    data: {
                        labels: weekly.map(d => d.week.slice(5)),
                        datasets: [{
                            label: '성공률 (%)',
                            data: weekly.map(d => d.success_rate * 100),
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.3,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { y: { beginAtZero: true, max: 100 } }
                    }
                });
            }
        },

        // =================================================================
        // Rule CRUD Methods
        // =================================================================

        async startEditRule(rule) {
            try {
                const response = await fetch(`${this.API_BASE_URL}/rules/${rule.id}`);
                if (!response.ok) throw new Error('규칙 조회 실패');
                this.editingRule = await response.json();
                this.editingRuleParamsJson = JSON.stringify(this.editingRule.ai_parameters || {}, null, 2);
                this.paramsValid = true;
            } catch (e) {
                this.showToast(e.message, 'error');
            }
        },

        cancelEditRule() {
            this.editingRule = null;
            this.editingRuleParamsJson = '{}';
        },

        validateParamsJson() {
            try {
                JSON.parse(this.editingRuleParamsJson);
                this.paramsValid = true;
            } catch {
                this.paramsValid = false;
            }
        },

        async saveEditRule() {
            if (!this.editingRule) return;
            try {
                let parsedParams = {};
                try { parsedParams = JSON.parse(this.editingRuleParamsJson); } catch { }

                const updates = {
                    field_name: this.editingRule.field_name,
                    rule_text: this.editingRule.rule_text,
                    condition: this.editingRule.condition,
                    note: this.editingRule.note,
                    is_active: this.editingRule.is_active,
                    is_common: this.editingRule.is_common,
                    ai_rule_type: this.editingRule.ai_rule_type,
                    ai_parameters: parsedParams,
                    ai_error_message: this.editingRule.ai_error_message
                };

                const response = await fetch(`${this.API_BASE_URL}/rules/${this.editingRule.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates)
                });
                if (!response.ok) throw new Error('저장 실패');
                this.showToast('규칙이 수정되었습니다.', 'success');
                this.editingRule = null;

                // 상세 페이지 새로고침
                if (this.ruleFileDetails) {
                    await this.viewRuleFileDetails(this.ruleFileDetails.id);
                }
            } catch (e) {
                this.showToast(e.message, 'error');
            }
        },

        async deleteRule(ruleId) {
            if (!confirm('이 규칙을 삭제(비활성화)하시겠습니까?')) return;
            try {
                const response = await fetch(`${this.API_BASE_URL}/rules/${ruleId}`, { method: 'DELETE' });
                if (!response.ok) throw new Error('삭제 실패');
                this.showToast('규칙이 삭제되었습니다.', 'success');
                if (this.ruleFileDetails) {
                    await this.viewRuleFileDetails(this.ruleFileDetails.id);
                }
            } catch (e) {
                this.showToast(e.message, 'error');
            }
        },

        async reinterpretSingleRule(ruleId) {
            try {
                this.showToast('규칙 재해석 중...', 'info');
                const response = await fetch(`${this.API_BASE_URL}/rules/${ruleId}/reinterpret?use_local_parser=true`, { method: 'POST' });
                if (!response.ok) throw new Error('재해석 실패');
                const result = await response.json();
                this.showToast(`재해석 완료: ${result.ai_rule_type} (${(result.ai_confidence_score * 100).toFixed(0)}%)`, 'success');
                if (this.ruleFileDetails) {
                    await this.viewRuleFileDetails(this.ruleFileDetails.id);
                }
            } catch (e) {
                this.showToast(e.message, 'error');
            }
        },

        openCreateRuleModal() {
            this.createRuleModalOpen = true;
            this.newRule = {
                rule_file_id: this.ruleFileDetails?.id || '',
                row_number: '0',
                column_name: '',
                rule_text: '',
                condition: '',
                ai_rule_type: 'custom',
                is_common: false
            };
        },

        async submitCreateRule() {
            if (!this.newRule.column_name || !this.newRule.rule_text) {
                this.showToast('컬럼명과 규칙 텍스트를 입력하세요.', 'error');
                return;
            }
            try {
                const payload = { ...this.newRule, rule_file_id: this.ruleFileDetails?.id || this.newRule.rule_file_id };
                const response = await fetch(`${this.API_BASE_URL}/rules/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!response.ok) throw new Error('규칙 생성 실패');
                this.showToast('규칙이 추가되었습니다.', 'success');
                this.createRuleModalOpen = false;
                if (this.ruleFileDetails) {
                    await this.viewRuleFileDetails(this.ruleFileDetails.id);
                }
            } catch (e) {
                this.showToast(e.message, 'error');
            }
        },

        // Fix logic helpers
        getSelectedFixCount() {
            const groups = this.getErrorsBySheetAndColumn();
            return this.selectedFixItems.reduce((sum, key) => sum + (groups.find(e => e.key === key)?.count || 0), 0);
        },

        hasFixableItems() { return this.getErrorsBySheetAndColumn().some(g => g.autoFixable); },
        isFixItemSelected(key) { return this.selectedFixItems.includes(key); },
        toggleFixItem(key, autoFixable) {
            if (!autoFixable) return;
            const idx = this.selectedFixItems.indexOf(key);
            if (idx === -1) this.selectedFixItems.push(key);
            else this.selectedFixItems.splice(idx, 1);
        },

        getUniqueSheets() { 
            const groups = this.getErrorsBySheetAndColumn();
            return [...new Set(groups.map(g => g.sheet))].sort(); 
        },
        
        getFilteredErrorsBySheetAndColumn() {
            const groups = this.getErrorsBySheetAndColumn();
            return this.fixFilterSheet === 'all' ? groups : groups.filter(g => g.sheet === this.fixFilterSheet);
        },

        selectAllFixableItems() {
            const groups = this.getFilteredErrorsBySheetAndColumn();
            const keys = groups.filter(g => g.autoFixable).map(g => g.key);
            this.selectedFixItems = [...new Set([...this.selectedFixItems, ...keys])];
        },

        getErrorsBySheetAndColumn() {
            if (!this.results || !this.results.errors) return [];
            const groupMap = {};
            for (const error of this.results.errors) {
                const sheet = error.sheet || '기본';
                const col = error.column;
                const key = `${sheet}::${col}`;
                if (!groupMap[key]) {
                    groupMap[key] = {
                        key, sheet, column: col, count: 0, sampleValues: [], ruleTypes: new Set(), messages: new Set(),
                        hasDatePattern: false, hasCommaNumber: false, hasGenderText: false
                    };
                }
                groupMap[key].count++;
                const valStr = String(error.actual_value || '').trim();
                const lowerCol = col.toLowerCase();
                if (!groupMap[key].hasDatePattern) {
                    if (/^\d{4}\s*[-\/\.]\s*\d{1,2}\s*[-\/\.]\s*\d{1,2}/.test(valStr) || 
                        ['date', '일자', '입사일', '생년월일', '퇴사일', '기준일'].some(k => lowerCol.includes(k))) {
                        groupMap[key].hasDatePattern = true;
                    }
                }
                if (!groupMap[key].hasCommaNumber) {
                    if (/^[\d,]+$/.test(valStr.replace(/\s/g, '')) && valStr.includes(',')) groupMap[key].hasCommaNumber = true;
                }
                if (!groupMap[key].hasGenderText) {
                    if (['남', '여', '남자', '여자', 'M', 'F', 'male', 'female'].includes(valStr.toLowerCase())) groupMap[key].hasGenderText = true;
                }
                if (groupMap[key].sampleValues.length < 20 && error.actual_value != null && !groupMap[key].sampleValues.includes(valStr)) {
                    groupMap[key].sampleValues.push(valStr);
                }
                if (error.rule_id) groupMap[key].ruleTypes.add(error.rule_id);
                if (error.message) groupMap[key].messages.add(error.message);
            }
            return Object.values(groupMap).map(item => {
                const { autoFixable, fixDescription, fixType } = this.determineAutoFixability(item);
                return { ...item, autoFixable, fixDescription, fixType, ruleTypes: Array.from(item.ruleTypes), messages: Array.from(item.messages) };
            }).sort((a, b) => a.sheet !== b.sheet ? a.sheet.localeCompare(b.sheet) : b.count - a.count);
        },

        determineAutoFixability(group) {
            const msgs = Array.from(group.messages).join(' ').toLowerCase();
            const col = group.column.toLowerCase();
            if (group.hasDatePattern) return { autoFixable: true, fixDescription: '날짜 형식 변환 (YYYY-MM-DD → YYYYMMDD)', fixType: 'date_format' };
            if (group.hasCommaNumber && (['숫자', 'number', '금액', 'wage', 'pay'].some(k => msgs.includes(k) || col.includes(k)))) return { autoFixable: true, fixDescription: '숫자 형식 변환 (콤마 제거)', fixType: 'number_format' };
            if (group.hasGenderText) return { autoFixable: true, fixDescription: '성별 코드 변환 (남→1, 여→2)', fixType: 'gender_code' };
            if (msgs.includes('공백')) return { autoFixable: true, fixDescription: '공백 제거', fixType: 'trim' };
            return { autoFixable: false, fixDescription: '수동 확인 필요', fixType: 'unknown' };
        },

        generateFixPreview() {
            if (this.selectedFixItems.length === 0) {
                this.fixPreview = { total: 0, success: 0, fail: 0, successRate: 0, items: [] };
                return;
            }
            const groups = this.getErrorsBySheetAndColumn();
            const previewItems = [];
            let successCount = 0;
            for (const error of this.results.errors) {
                const key = `${error.sheet || '기본'}::${error.column}`;
                if (!this.selectedFixItems.includes(key)) continue;
                const group = groups.find(g => g.key === key);
                const fixType = group?.fixType || 'unknown';
                const beforeValue = error.actual_value;
                const afterValue = this.simulateFixValue(beforeValue, fixType);
                const success = afterValue !== null && afterValue !== beforeValue;
                previewItems.push({ sheet: error.sheet || '기본', column: error.column, row: error.row, before: String(beforeValue ?? ''), after: String(afterValue ?? beforeValue ?? ''), success, fixType });
                if (success) successCount++;
            }
            const total = previewItems.length;
            this.fixPreview = { total, success: successCount, fail: total - successCount, successRate: total > 0 ? Math.round((successCount / total) * 100) : 0, items: previewItems };
        },

        simulateFixValue(value, fixType) {
            if (value == null) return null;
            const str = String(value).trim();
            if (fixType === 'date_format') {
                const m = str.match(/^(\d{4})\s*[-\/\.]\s*(\d{1,2})\s*[-\/\.]\s*(\d{1,2})/);
                return m ? `${m[1]}${m[2].padStart(2, '0')}${m[3].padStart(2, '0')}` : null;
            }
            if (fixType === 'gender_code') {
                const map = { '남': '1', '남자': '1', 'm': '1', 'male': '1', '여': '2', '여자': '2', 'f': '2', 'female': '2' };
                return map[str] || null;
            }
            if (fixType === 'number_format') {
                const cleaned = str.replace(/[,\s]/g, '');
                return /^\d+$/.test(cleaned) ? cleaned : null;
            }
            return fixType === 'trim' ? str : null;
        },

        getFilteredPreviewItems() {
            if (!this.fixPreview.items) return [];
            if (this.fixPreviewFilter === 'success') return this.fixPreview.items.filter(i => i.success);
            if (this.fixPreviewFilter === 'fail') return this.fixPreview.items.filter(i => !i.success);
            return this.fixPreview.items;
        },

        async downloadFixedFile() {
            if (this.selectedFixItems.length === 0 || !this.fileA) return;
            this.isDownloading = true;
            try {
                const groups = this.getErrorsBySheetAndColumn();
                const cellsToFix = this.results.errors.filter(e => this.selectedFixItems.includes(`${e.sheet || '기본'}::${e.column}`))
                    .map(e => ({ 
                        sheet: e.sheet, 
                        row: e.row, 
                        column: e.column, 
                        currentValue: e.actual_value, 
                        fixType: groups.find(g => g.key === `${e.sheet || '기본'}::${e.column}`)?.fixType || 'unknown' 
                    }));
                const formData = new FormData();
                formData.append('original_file', this.fileA);
                formData.append('cells_to_fix_json', JSON.stringify(cellsToFix));
                const res = await fetch(`${this.API_BASE_URL}/api/fix/download`, { method: 'POST', body: formData });
                if (!res.ok) throw new Error('파일 생성 실패');
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `수정완료_${this.fileA.name}`;
                document.body.appendChild(a); a.click(); document.body.removeChild(a);
                this.showToast('파일이 다운로드되었습니다.', 'success');
            } catch (e) { this.showToast(e.message, 'error'); } 
            finally { this.isDownloading = false; }
        },

        // Helper UI
        get hasResults() { return this.results !== null; },
        calculateComplianceRate() {
            if (!this.results || !this.results.summary) return 0;
            const { total_rows, valid_rows } = this.results.summary;
            return total_rows > 0 ? Math.round((valid_rows / total_rows) * 100) : 0;
        },
        getSelectedSheetSummary() {
            if (!this.selectedSheet || !this.results?.metadata?.sheets_summary) return null;
            return this.results.metadata.sheets_summary[this.selectedSheet];
        },
        showToast(message, type = 'info') {
            const id = Date.now();
            this.toasts.push({ id, message, type, show: true, title: type === 'success' ? '성공' : '알림' });
            setTimeout(() => {
                const t = this.toasts.find(toast => toast.id === id);
                if (t) t.show = false;
            }, 3000);
        },
        renderCharts() {
            if (!this.results?.metadata?.sheets_summary) return;
            const ctx = document.getElementById('sheetChart');
            if (!ctx) return;
            if (this.chartInstance) this.chartInstance.destroy();
            const s = this.results.metadata.sheets_summary;
            const labels = this.results.metadata.sheet_order || Object.keys(s);
            this.chartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [
                        { label: '오류 행', data: labels.map(l => s[l]?.error_rows || 0), backgroundColor: '#ef4444' },
                        { label: '정상 행', data: labels.map(l => s[l]?.valid_rows || 0), backgroundColor: '#22c55e' }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { x: { stacked: true }, y: { stacked: true } } }
            });
        },
        resetResults() {
            this.results = null;
            this.selectedRuleDetailId = null;
            if (this.chartInstance) { this.chartInstance.destroy(); this.chartInstance = null; }
        },

        // =================================================================
        // AI Smart Analysis Methods
        // =================================================================

        handleSmartAnalysisFileSelect(event) {
            const file = event.target.files[0];
            if (file) this.smartAnalysisFileA = file;
        },

        handleSmartAnalysisFileDrop(event) {
            const file = event.dataTransfer.files[0];
            if (file) this.smartAnalysisFileA = file;
        },

        getSmartAnalysisFile() {
            // 이미 업로드된 검증용 파일이 있으면 재활용, 없으면 전용 파일 사용
            return this.smartAnalysisFileA || this.fileA;
        },

        async runCrossFieldAnalysis() {
            const file = this.getSmartAnalysisFile();
            if (!file) {
                this.showToast('분석할 파일을 먼저 선택해주세요.', 'error');
                return;
            }
            this.smartAnalysisLoading = true;
            this.crossFieldResults = null;
            try {
                const formData = new FormData();
                formData.append('employee_file', file);
                formData.append('ai_provider', this.aiProvider);
                const response = await fetch(`${this.API_BASE_URL}/ai/cross-field-analysis`, {
                    method: 'POST', body: formData
                });
                if (!response.ok) throw new Error('분석 실패');
                this.crossFieldResults = await response.json();
                this.showToast(`크로스필드 분석 완료: ${this.crossFieldResults.total_issues}건 발견`, 'success');
            } catch (e) {
                this.showToast('크로스필드 분석 중 오류: ' + e.message, 'error');
            } finally {
                this.smartAnalysisLoading = false;
            }
        },

        async runDataProfile() {
            const file = this.getSmartAnalysisFile();
            if (!file) {
                this.showToast('분석할 파일을 먼저 선택해주세요.', 'error');
                return;
            }
            this.smartAnalysisLoading = true;
            this.dataProfileResults = null;
            try {
                const formData = new FormData();
                formData.append('employee_file', file);
                formData.append('ai_provider', this.aiProvider);
                const response = await fetch(`${this.API_BASE_URL}/ai/data-profile`, {
                    method: 'POST', body: formData
                });
                if (!response.ok) throw new Error('프로파일링 실패');
                this.dataProfileResults = await response.json();
                this.showToast(`데이터 프로파일링 완료: 건강점수 ${this.dataProfileResults.health_score}점`, 'success');
            } catch (e) {
                this.showToast('데이터 프로파일링 중 오류: ' + e.message, 'error');
            } finally {
                this.smartAnalysisLoading = false;
            }
        },

        getFilteredCrossFieldResults() {
            if (!this.crossFieldResults?.contradictions) return [];
            if (this.crossFieldSeverityFilter === 'all') return this.crossFieldResults.contradictions;
            return this.crossFieldResults.contradictions.filter(c => c.severity === this.crossFieldSeverityFilter);
        },

        getFilteredProfileFindings() {
            if (!this.dataProfileResults?.findings) return [];
            if (this.profileCategoryFilter === 'all') return this.dataProfileResults.findings;
            return this.dataProfileResults.findings.filter(f => f.category === this.profileCategoryFilter);
        },

        getProfileCategories() {
            if (!this.dataProfileResults?.findings) return [];
            const cats = new Set(this.dataProfileResults.findings.map(f => f.category));
            const labels = {
                missing_data: '결측 데이터',
                format_inconsistency: '형식 불일치',
                statistical_outlier: '통계적 이상치',
                duplicate_suspect: '중복 의심',
                semantic_anomaly: '의미적 이상',
                business_logic: '비즈니스 로직',
                pattern_break: '패턴 이상',
                other: '기타'
            };
            return Array.from(cats).map(c => ({ value: c, label: labels[c] || c }));
        },

        getSeverityColor(severity) {
            return { high: 'text-red-600 bg-red-50 border-red-200', medium: 'text-amber-600 bg-amber-50 border-amber-200', low: 'text-blue-600 bg-blue-50 border-blue-200' }[severity] || 'text-slate-600 bg-slate-50 border-slate-200';
        },

        getSeverityBadge(severity) {
            return { high: 'bg-red-100 text-red-700', medium: 'bg-amber-100 text-amber-700', low: 'bg-blue-100 text-blue-700' }[severity] || 'bg-slate-100 text-slate-700';
        },

        getSeverityLabel(severity) {
            return { high: '심각', medium: '주의', low: '참고' }[severity] || severity;
        },

        getHealthScoreColor(score) {
            if (score >= 80) return 'text-green-600';
            if (score >= 60) return 'text-amber-600';
            return 'text-red-600';
        },

        getHealthScoreGradient(score) {
            if (score >= 80) return 'from-green-500 to-emerald-600';
            if (score >= 60) return 'from-amber-500 to-orange-600';
            return 'from-red-500 to-rose-600';
        }
    };
}