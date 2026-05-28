classdef QZS_App < matlab.apps.AppBase

    % --- 界面组件属性声明 ---
    properties (Access = public)
        UIWindow               matlab.ui.Figure
        LeftPanel              matlab.ui.container.Panel
        RightTabGroup          matlab.ui.container.TabGroup
        
        % 5个标签页完全对应原脚本的 6 个 Figure 核心功能
        Tab1, Tab2, Tab3, Tab4, Tab5
        
        % 图像坐标轴句柄
        Ax1, Ax2, Ax3, Ax3_Inset, Ax4, Ax5
        AxGeom                 matlab.ui.control.UIAxes % <-- 修正2：更改为标准的 UIAxes 类名
        
        % 控制面板控件
        DeltaHatEdit          matlab.ui.control.NumericEditField
        AHatEdit              matlab.ui.control.NumericEditField
        AlphaEdit             matlab.ui.control.NumericEditField
        Alpha1Edit            matlab.ui.control.NumericEditField
        GammaEdit             matlab.ui.control.NumericEditField
        ATargetEdit           matlab.ui.control.NumericEditField
        TauPEdit              matlab.ui.control.NumericEditField
        GEdit                 matlab.ui.control.NumericEditField
        CEdit                 matlab.ui.control.NumericEditField
        ZeEdit                matlab.ui.control.NumericEditField
        ExcelPathEdit         matlab.ui.control.EditField
        
        % 交互按钮
        RunCalcButton         matlab.ui.control.Button
        LoadCSVButton         matlab.ui.control.Button
        
        % 系统日志输出
        LogTextArea           matlab.ui.control.TextArea
    end
    
    % --- 内部核心数据属性（严格保留原代码变量） ---
    properties (Access = private)
        y_hat, test_params
        f0_val, Ze_hat_val, zeta_val
        v_in_data, t_matrix, fs_rate, N_points
        v_out_matrix, f_psd_vec, v_in_psd_vec, v_out_psd_matrix
    end

    % --- UI界面初始化布局 ---
    methods (Access = private)
        function createComponents(app)
            % 创建主窗口
            app.UIWindow = uifigure('Name', '准零刚度(QZS)隔振系统非线性动力学交互分析平台', 'Position', [100 100 1250 820]);
            
            % 左侧控制面板
            app.LeftPanel = uipanel(app.UIWindow, 'Title', '系统物理与几何参数设置', 'Position', [10 10 340 800], 'FontWeight', 'bold');
            
            % 参数输入组件排布
            uilabel(app.LeftPanel, 'Position', [15 745 120 22], 'Text', 'delta_hat (δ̂):');
            app.DeltaHatEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 745 160 22], 'Value', 0.5);
            
            uilabel(app.LeftPanel, 'Position', [15 715 120 22], 'Text', 'a_hat (â):');
            app.AHatEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 715 160 22], 'Value', 0.755);
            
            uilabel(app.LeftPanel, 'Position', [15 685 120 22], 'Text', 'alpha (α):');
            app.AlphaEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 685 160 22], 'Value', 0.942);
            
            uilabel(app.LeftPanel, 'Position', [15 655 120 22], 'Text', 'alpha1 (α₁):');
            app.Alpha1Edit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 655 160 22], 'Value', 0.501);
            
            uilabel(app.LeftPanel, 'Position', [15 625 120 22], 'Text', 'gamma (γ):');
            app.GammaEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 625 160 22], 'Value', 2.143);
            
            uilabel(app.LeftPanel, 'Position', [15 585 120 22], 'Text', '屏蔽内径 a (mm):');
            app.ATargetEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 585 160 22], 'Value', 60);
            
            uilabel(app.LeftPanel, 'Position', [15 555 120 22], 'Text', '许用切应力 τ_p(Mpa):');
            app.TauPEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 555 160 22], 'Value', 70);
            
            uilabel(app.LeftPanel, 'Position', [15 525 120 22], 'Text', '切变模量 G(Mpa):');
            app.GEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 525 160 22], 'Value', 75000);
            
            uilabel(app.LeftPanel, 'Position', [15 485 120 22], 'Text', '阻尼系数 c:');
            app.CEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 485 160 22], 'Value', 20);
            
            uilabel(app.LeftPanel, 'Position', [15 455 120 22], 'Text', '激励幅值 Ze(mm):');
            app.ZeEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [150 455 160 22], 'Value', 3);
            
            uilabel(app.LeftPanel, 'Position', [15 415 120 22], 'Text', 'Excel导出路径:');
            app.ExcelPathEdit = uieditfield(app.LeftPanel, 'text', 'Position', [150 415 160 22], 'Value', pwd);
            
            % 操作控制按钮
            app.RunCalcButton = uibutton(app.LeftPanel, 'push', 'Position', [15 365 295 35], ...
                'Text', '1. 运行刚度匹配并导出Excel', 'FontWeight', 'bold', ...
                'ButtonPushedFcn', @(btn, event) app.calculateAndExportSprings());
            
            app.LoadCSVButton = uibutton(app.LeftPanel, 'push', 'Position', [15 320 295 35], ...
                'Text', '2. 载入外部振动与参考CSV数据', 'FontWeight', 'bold', ...
                'ButtonPushedFcn', @(btn, event) app.processVibrationSignals());
            
            % 日志区域
            uilabel(app.LeftPanel, 'Position', [15 285 100 22], 'Text', '运行日志输出:');
            app.LogTextArea = uitextarea(app.LeftPanel, 'Position', [15 15 295 265], 'Editable', 'off');
            
            % 右侧标签页组
            app.RightTabGroup = uitabgroup(app.UIWindow, 'Position', [360 10 880 800]);
            app.Tab1 = uitab(app.RightTabGroup, 'Title', '无量纲力/刚度曲线(Fig.1)');
            app.Tab2 = uitab(app.RightTabGroup, 'Title', '5组刚度曲线对比(Fig.2)');
            app.Tab3 = uitab(app.RightTabGroup, 'Title', '位移传递率分析(Fig.3/4)');
            app.Tab4 = uitab(app.RightTabGroup, 'Title', '时域电压响应(Fig.5)');
            app.Tab5 = uitab(app.RightTabGroup, 'Title', '功率谱密度PSD对比(Fig.6)');
            
            % --- 新增几何机构标签页 ---
            tabGeom = uitab(app.RightTabGroup, 'Title', '机构几何装配图');
            
            % 初始化各坐标轴
            app.Ax1 = uiaxes(app.Tab1, 'Position', [60 80 760 640]);
            app.Ax2 = uiaxes(app.Tab2, 'Position', [60 80 760 640]);
            app.Ax3 = uiaxes(app.Tab3, 'Position', [60 80 760 640]);
            app.Ax3_Inset = uiaxes(app.Tab3, 'Position', [540 380 240 240]); % 嵌套图小窗口
            app.Ax4 = uiaxes(app.Tab4, 'Position', [40 40 800 680]); % 3x2子图大画布
            app.Ax5 = uiaxes(app.Tab5, 'Position', [60 80 760 640]);
            app.AxGeom = uiaxes(tabGeom, 'Position', [60 80 760 640]); % <-- 修正2：几何画布初始化
        end
    end

    % --- 构造函数与私有数据初始化 ---
    methods (Access = public)
        function app = QZS_App()
            app.createComponents();
            
            % 严格复现原脚本内置的 y_hat 区间与 5 组标准对比参数矩阵
            app.y_hat = linspace(-10, 10, 1000);
            app.test_params = [
                0.500, 0.755, 2.143, 0.942, 0.501;
                0.471, 1.000, 1.054, 2.684, 0.179;
                0.800, 0.800, 1.987, NaN, NaN;
                0.500, 0.800, 1.987, NaN, NaN;
                0.200, 0.800, 2.192, NaN, NaN];
                
            app.UIWindow.Visible = 'on';
            app.addLog('系统就绪。请配置参数后点击“运行刚度匹配并导出Excel”按钮。');
        end
    end

    methods (Access = private)
        % =================================================================
        % 核心算法内核：严格复现原脚本前半部分的弹簧选型、校验以及 Excel 导出
        % =================================================================
        function calculateAndExportSprings(app)
            app.LogTextArea.Value = ""; 
            app.addLog('>>> 开始根据目标无量纲参数反求物理弹簧及结构尺寸...');
            
            % 1. 获取界面输入
            delta_hat_t = app.DeltaHatEdit.Value;
            a_hat_t     = app.AHatEdit.Value;
            alpha_t     = app.AlphaEdit.Value;
            alpha1_t    = app.Alpha1Edit.Value;
            gamma_t     = app.GammaEdit.Value;
            a_target    = app.ATargetEdit.Value;
            tau_p       = app.TauPEdit.Value;
            G           = app.GEdit.Value;
            g           = 9.81;
            
            % 2. 严格执行几何原长与预压缩量推导
            h1_target = sqrt(a_target^2 * (1/a_hat_t^2 - 1));
            delta_target = delta_hat_t * sqrt(a_target^2 + h1_target^2);
            L1 = sqrt(a_target^2 + h1_target^2) + delta_target;
            
            d_target_geom = h1_target / (gamma_t - 1);
            h_target = h1_target + d_target_geom;
            h2_target = h1_target + 2*d_target_geom;
            
            rho_target = (1 - a_hat_t^2) / (gamma_t - 1)^2;
            delta_hat1_target = 1 - sqrt(1 + 2*sqrt(1 - a_hat_t^2)*sqrt(rho_target) + rho_target) + delta_hat_t;
            delta_hat2_target = 1 - sqrt(1 + 4*sqrt(1 - a_hat_t^2)*sqrt(rho_target) + 4*rho_target) + delta_hat_t;
            delta1_target = delta_hat1_target * sqrt(a_target^2 + h1_target^2);
            delta2_target = delta_hat2_target * sqrt(a_target^2 + h1_target^2);
            
            L2 = sqrt(a_target^2 + h_target^2) + delta1_target;
            L3 = sqrt(a_target^2 + h2_target^2) + delta2_target;
            
            % 3. 弹簧选型公式
            d1_w = 1.2; D1_w = 15.6; n1_w = 15;
            k_1 = (G * d1_w^4) / (8 * D1_w^3 * n1_w) * 1000;
            
            d2_w = 1.2; D2_w = 15.6; n2_w = 14;
            k2 = (G * d2_w^4) / (8 * D2_w^3 * n2_w) * 1000;
            
            d3_w = 1.2; D3_w = 15.6; n3_w = 30;
            k_3 = (G * d3_w^4) / (8 * D3_w^3 * n3_w) * 1000;
            
            M_computed = (k2 * 1.229 * sqrt((a_target/1000)^2 + (h1_target/1000)^2)) / g;
            app.addLog(sprintf('结构计算：h1=%.1fmm, δ=%.1fmm, 自动匹配负载 M=%.2f kg', h1_target, delta_target, M_computed));
            
            % 4. 最佳理论平衡压缩量推导
            k1 = k2 * alpha_t;
            k3 = k2 * alpha1_t;
            f1 = -(k1/1000)*delta_target*(h1_target/sqrt(a_target^2+h1_target^2));
            f3 = -(k3/1000)*delta1_target*(h_target/sqrt(a_target^2+h_target^2));
            f4 = -(k1/1000)*delta2_target*(h2_target/sqrt(a_target^2+h2_target^2));
            f2 = -(2*f1 + 2*f3 + 2*f4);
            delta3_target = f2 / (k2/1000);
            L = h2_target + delta3_target;
            
            % 5. 循环迭代弹簧组合存储至 Excel
            C_range = 5:1:12; 
            ratio_range = 0.28:0.01:0.5;
            
            k2_results = [];
            for C = C_range
                for ratio = ratio_range
                    a_coef = (G*ratio)/(8*(C^4)*(k2/1000));
                    D_val = (-2/C + sqrt(4/(C^2) + 4*a_coef*L)) / (2*a_coef);
                    d_val = D_val / C;
                    D_out = D_val + d_val;
                    K_factor = (4*C-1)/(4*C-4) + 0.615/C;
                    d_tgt = 1.6*sqrt(K_factor*C*M_computed*g/tau_p);
                    n_val = (G*D_val) / (8*(C^4)*(k2/1000));
                    k2_act = (G*D_val) / (8*(C^4)*n_val);
                    p_val = ratio * D_val;
                    k2_results = [k2_results; d_tgt, d_val, D_val, D_out, C, n_val, ratio, p_val, G, L, k2_act*1000];
                end
            end
            k2_table = array2table(k2_results, 'VariableNames', {'d_target_mm', 'd_mm', 'D_mm','D_out_mm','C', 'n', 'ratio', 'p_mm', 'G_Mpa', 'L_mm', 'k_actual_N_m'});
            [~, ia] = unique(k2_table(:, {'C', 'ratio'}), 'rows'); k2_table = k2_table(ia, :);

            k1_results = [];
            for C1 = C_range
                for ratio1 = ratio_range
                    a1 = (G*ratio1)/(8*(C1^4)*(k1/1000));
                    D1 = (-2/C1 + sqrt(4/(C1^2) + 4*a1*L1)) / (2*a1);
                    d1 = D1 / C1; D_out1 = D1 + d1;
                    K1_f = (4*C1-1)/(4*C1-4) + 0.615/C1;
                    d1_tgt = 1.6*sqrt(K1_f*C1*M_computed*g/tau_p);
                    n1_val = (G*D1) / (8*(C1^4)*(k1/1000));
                    k1_act = (G*D1) / (8*(C1^4)*n1_val);
                    p1_val = ratio1 * D1;
                    k1_results = [k1_results; d1_tgt, d1, D1, D_out1, C1, n1_val, ratio1, p1_val, G, L1, k1_act*1000];
                end
            end
            k1_table = array2table(k1_results, 'VariableNames', {'d_target_mm', 'd_mm', 'D_mm','D_out_mm', 'C', 'n', 'ratio', 'p_mm', 'G_Mpa', 'L_mm', 'k_actual_N_m'});
            [~, ia] = unique(k1_table(:, {'C', 'ratio'}), 'rows'); k1_table = k1_table(ia, :);

            k3_results = [];
            for C2 = C_range
                for ratio2 = ratio_range
                    a2 = (G*ratio2)/(8*(C2^4)*(k3/1000));
                    D2 = (-2/C2 + sqrt(4/(C2^2) + 4*a2*L2)) / (2*a2);
                    d2 = D2 / C2; D_out2 = D2 + d2;
                    K2_f = (4*C2-1)/(4*C2-4) + 0.615/C2;
                    d2_tgt = 1.6*sqrt(K2_f*C2*M_computed*g/tau_p);
                    n2_val = (G*D2) / (8*(C2^4)*(k3/1000));
                    k3_act = (G*D2) / (8*(C2^4)*n2_val);
                    p2_val = ratio2 * D2;
                    k3_results = [k3_results; d2_tgt, d2, D2, D_out2, C2, n2_val, ratio2, p2_val, G, L2, k3_act*1000];
                end
            end
            k3_table = array2table(k3_results, 'VariableNames', {'d_target_mm', 'd_mm', 'D_mm','D_out_mm', 'C', 'n', 'ratio', 'p_mm', 'G_Mpa', 'L_mm', 'k_actual_N_m'});
            [~, ia] = unique(k3_table(:, {'C', 'ratio'}), 'rows'); k3_table = k3_table(ia, :);

            try
                excel_filename = fullfile(app.ExcelPathEdit.Value, 'Spring_Parameters.xlsx');
                writetable(k2_table, excel_filename, 'Sheet', 'K2_Spring');
                writetable(k1_table, excel_filename, 'Sheet', 'Up_Down_Spring');
                writetable(k3_table, excel_filename, 'Sheet', 'Middle_Spring');
                app.addLog(['成功导出弹簧参数表至：', excel_filename]);
            catch ME
                app.addLog(['Excel导出失败: ', ME.message]);
            end
            
            % 6. 存储常量
            app.f0_val = (sqrt(k2/M_computed)) / (2*pi);
            app.Ze_hat_val = (app.ZeEdit.Value / 1000) / sqrt((a_target/1000)^2 + (h1_target/1000)^2);
            app.zeta_val = app.CEdit.Value * (sqrt(k2/M_computed)) / (2 * k2);

            % 7. 渲染静态分析图与新加的位置示意图
            app.plotStaticFigures(h1_target, h2_target, a_target, rho_target, delta_hat_t, delta_hat1_target, delta_hat2_target, alpha_t, alpha1_t);
            app.plotMechanismGeometry(a_target, h1_target, h_target, h2_target); % <-- 联动触发
        end
        
        % =================================================================
        % 静态特性绘图引擎
        % =================================================================
        function plotStaticFigures(app, h1_t, h2_t, a_t, rho_t, delta_hat_t, delta_hat1_t, delta_hat2_t, alpha_t, alpha1_t)
            cla(app.Ax1, 'reset');
            x_e_hat_tgt = sqrt(1 - app.AHatEdit.Value^2) + sqrt(rho_t);
            K_hat_c1 = zeros(size(app.y_hat)); f_hat_c1 = zeros(size(app.y_hat)); y_hat_c1 = zeros(size(app.y_hat));
            
            for i = 1:length(app.y_hat)
                xi_h = x_e_hat_tgt + app.y_hat(i);
                P1 = sqrt(1 - app.AHatEdit.Value^2) - xi_h;
                P2 = 1 - 2*sqrt(1 - app.AHatEdit.Value^2)*xi_h + xi_h^2;
                P3 = 1 + delta_hat_t;
                P4 = sqrt(1 - app.AHatEdit.Value^2 + rho_t + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t)) - xi_h;
                P5 = 1 + rho_t + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t) - 2*sqrt(1 - app.AHatEdit.Value^2 + rho_t + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t))*xi_h + xi_h^2;
                P6 = sqrt(1 + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t) + rho_t) + delta_hat1_t;
                P7 = sqrt(1 - app.AHatEdit.Value^2) + 2*sqrt(rho_t) - xi_h;
                P8 = 1 + 4*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t) + 4*rho_t - 2*(sqrt(1 - app.AHatEdit.Value^2) + 2*sqrt(rho_t))*xi_h + xi_h^2;
                P9 = sqrt(1 + 4*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t) + 4*rho_t) + delta_hat2_t;
                
                dP2 = -2*sqrt(1 - app.AHatEdit.Value^2) + 2*xi_h;
                dP5 = -2*sqrt(1 - app.AHatEdit.Value^2 + rho_t + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t)) + 2*xi_h;
                dP8 = -2*(sqrt(1 - app.AHatEdit.Value^2) + 2*sqrt(rho_t)) + 2*xi_h;
                
                dN1 = -2 * alpha_t * (1 - P3 * P2^(-0.5)) * (-1) - alpha_t * P1 * P2^(-1.5) * P3 * dP2;
                dN3 = -2 * alpha1_t * (1 - P6 * P5^(-0.5)) * (-1) - alpha1_t * P4 * P5^(-1.5) * P6 * dP5;
                dN5 = -2 * alpha_t * (1 - P9 * P8^(-0.5)) * (-1) - alpha_t * P7 * P8^(-1.5) * P9 * dP8;
                
                K_hat_c1(i) = 1 + dN1 + dN3 + dN5;
                f_hat_c1(i) = xi_h - 2*alpha_t * P1*(sqrt(P2)-P3)/sqrt(P2) - 2*alpha1_t * P4*(sqrt(P5)-P6)/sqrt(P5) - 2*alpha_t * P7*(sqrt(P8)-P9)/sqrt(P8);
                y_hat_c1(i) = xi_h - x_e_hat_tgt;
            end
            
            yyaxis(app.Ax1, 'left');
            plot(app.Ax1, y_hat_c1, f_hat_c1, 'Color', [0, 0.4470, 0.7410], 'LineWidth', 2.5);
            ylabel(app.Ax1, 'Dimensionless Force \bf\hat{f}');
            app.Ax1.YLim = [-6, 6]; app.Ax1.XLim = [-3, 3];
            
            yyaxis(app.Ax1, 'right');
            plot(app.Ax1, y_hat_c1, K_hat_c1, 'Color', [0.8500, 0.3250, 0.0980], 'LineStyle', '--', 'LineWidth', 2.5);
            ylabel(app.Ax1, 'Dimensionless Stiffness \bf\hat{K}');
            
            grid(app.Ax1, 'on');
            xlabel(app.Ax1, 'Dimensionless Displacement \bf\hat{y}');
            title(app.Ax1, 'Dimensionless Force and Stiffness Curves (Target Parameters)');
            
            % TAB 2 绘制
            cla(app.Ax2); hold(app.Ax2, 'on'); grid(app.Ax2, 'on');
            num_test = size(app.test_params, 1); base_colors = lines(num_test); line_styles = {'-', '--', ':', '-.', '-'};
            
            for j = 1:num_test
                d_h = app.test_params(j,1); a_h = app.test_params(j,2); g_h = app.test_params(j,3);
                if ~isnan(app.test_params(j,4))
                    al = app.test_params(j,4); al1 = app.test_params(j,5);
                else
                    Dlt = sqrt(1 + a_h^2 * g_h^2 - 2 * a_h^2 * g_h); Dlt1 = (1 + d_h) * (g_h - 1); Dlt2 = (1 + d_h) * (g_h - 1)^3;
                    C1 = 6*(1 + d_h) * a_h^(-3) / (-12*Dlt2/Dlt^3 + 72*Dlt2*(1-a_h^2)/Dlt^5 - 60*Dlt2*(1-a_h^2)^2/Dlt^7);
                    al1 = -1/(C1*(4-4*Dlt1/Dlt + 4*(1-a_h^2)*Dlt1/Dlt^3) + 2*(1-(1 + d_h)/a_h)); al = C1 * al1;
                end
                
                K_hat_loop = zeros(size(app.y_hat));
                rho_loop = (1 - a_h^2) / (g_h - 1)^2;
                dh1_loop = 1 - sqrt(1 + 2*sqrt(1 - a_h^2)*sqrt(rho_loop) + rho_loop) + d_h;
                dh2_loop = 1 - sqrt(1 + 4*sqrt(1 - a_h^2)*sqrt(rho_loop) + 4*rho_loop) + d_h;
                xe_loop = sqrt(1 - a_h^2) + sqrt(rho_loop);
                
                for i = 1:length(app.y_hat)
                    xi_h = xe_loop + app.y_hat(i);
                    P1 = sqrt(1 - a_h^2) - xi_h; P2 = 1 - 2*sqrt(1 - a_h^2)*xi_h + xi_h^2; P3 = 1 + d_h;
                    P4 = sqrt(1 - a_h^2 + rho_loop + 2*sqrt(1 - a_h^2)*sqrt(rho_loop)) - xi_h;
                    P5 = 1 + rho_loop + 2*sqrt(1 - a_h^2)*sqrt(rho_loop) - 2*sqrt(1 - a_h^2 + rho_loop + 2*sqrt(1 - a_h^2)*sqrt(rho_loop))*xi_h + xi_h^2;
                    P6 = sqrt(1 + 2*sqrt(1 - a_h^2)*sqrt(rho_loop) + rho_loop) + dh1_loop;
                    P7 = sqrt(1 - a_h^2) + 2*sqrt(rho_loop) - xi_h;
                    P8 = 1 + 4*sqrt(1 - a_h^2)*sqrt(rho_loop) + 4*rho_loop - 2*(sqrt(1 - a_h^2) + 2*sqrt(rho_loop))*xi_h + xi_h^2;
                    P9 = sqrt(1 + 4*sqrt(1 - a_h^2)*sqrt(rho_loop) + 4*rho_loop) + dh2_loop;
                    
                    dP2 = -2*sqrt(1 - a_h^2) + 2*xi_h; dP5 = -2*sqrt(1 - a_h^2 + rho_loop + 2*sqrt(1 - a_h^2)*sqrt(rho_loop)) + 2*xi_h; dP8 = -2*(sqrt(1 - a_h^2) + 2*sqrt(rho_loop)) + 2*xi_h;
                    dN1 = -2 * al * (1 - P3 * P2^(-0.5)) * (-1) - al * P1 * P2^(-1.5) * P3 * dP2;
                    dN3 = -2 * al1 * (1 - P6 * P5^(-0.5)) * (-1) - al1 * P4 * P5^(-1.5) * P6 * dP5;
                    dN5 = -2 * al * (1 - P9 * P8^(-0.5)) * (-1) - al * P7 * P8^(-1.5) * P9 * dP8;
                    K_hat_loop(i) = 1 + dN1 + dN3 + dN5;
                end
                lbl = sprintf('δ̂=%.3f, â=%.3f, γ=%.3f, α=%.3f, α₁=%.3f', d_h, a_h, g_h, al, al1);
                plot(app.Ax2, app.y_hat, K_hat_loop, 'Color', base_colors(j,:), 'LineStyle', line_styles{j}, 'LineWidth', 2.5, 'DisplayName', lbl);
            end
            xline(app.Ax2, 0, '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 1.5, 'HandleVisibility', 'off');
            app.Ax2.XLim = [-0.8, 0.8]; app.Ax2.YLim = [0, 1.5];
            xlabel(app.Ax2, '\bf\hat{y}'); ylabel(app.Ax2, '\bf\hat{K}');
            title(app.Ax2, 'Stiffness Curves Comparison of QZS'); legend(app.Ax2, 'Location', 'best');
            hold(app.Ax2, 'off');
            
            app.plotTransmissibilityCurves();
        end

        % =================================================================
        % 传递率计算器
        % =================================================================
        function plotTransmissibilityCurves(app)
            cla(app.Ax3); hold(app.Ax3, 'on'); grid(app.Ax3, 'on');
            cla(app.Ax3_Inset); hold(app.Ax3_Inset, 'on'); grid(app.Ax3_Inset, 'on');
            
            mu1_vals = [0.1907, 0.1188, 0.00048, 0.3367, 0.2189]; mu3_vals = [1.3836, 1.2344, 0.0017,  0.3876, 0.2104];
            f_ex = linspace(0.1, 10, 1000); f_inset = linspace(6, 10, 200);
            colors_map = {[0 0.4470 0.7410], [0.8500 0.3250 0.0980], [0.4660 0.6740 0.1880], [0.4940 0.1840 0.5560], [0.3010 0.7450 0.9330]}; styles = {'--', '-', '-.', ':', '-'};
            
            for i = 1:5
                Ta_main = zeros(size(f_ex)); Ta_ins = zeros(size(f_inset));
                for j = 1:length(f_ex)
                    Omega = f_ex(j) / app.f0_val; Ta_main(j) = app.compute_transmissibility(mu1_vals(i), mu3_vals(i), Omega, app.Ze_hat_val, app.zeta_val);
                end
                for j = 1:length(f_inset)
                    Omega = f_inset(j) / app.f0_val; Ta_ins(j) = app.compute_transmissibility(mu1_vals(i), mu3_vals(i), Omega, app.Ze_hat_val, app.zeta_val);
                end
                lbl = sprintf('Group %d: \\mu_1=%.4f, \\mu_3=%.4f', i, mu1_vals(i), mu3_vals(i));
                plot(app.Ax3, f_ex, Ta_main, 'Color', colors_map{i}, 'LineStyle', styles{i}, 'LineWidth', 2.0, 'DisplayName', lbl);
                plot(app.Ax3_Inset, f_inset, Ta_ins, 'Color', colors_map{i}, 'LineStyle', styles{i}, 'LineWidth', 1.5);
            end
            yline(app.Ax3, 1, '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 1.5, 'HandleVisibility', 'off');
            app.Ax3.XLim = [0, 10]; app.Ax3.YLim = [0, 10];
            xlabel(app.Ax3, 'Frequency (Hz)'); ylabel(app.Ax3, 'Transmissibility T_a');
            title(app.Ax3, sprintf('Displacement Transmissibility (\\zeta = %.3f, Z_e = %.1fmm)', app.zeta_val, app.ZeEdit.Value));
            legend(app.Ax3, 'Location', 'northeast', 'FontSize', 9);
            app.Ax3_Inset.XLim = [6, 10]; app.Ax3_Inset.YLim = [0, 0.25];
            hold(app.Ax3, 'off'); hold(app.Ax3_Inset, 'off');
            app.addLog(sprintf('理论计算匹配就绪：参考原频 f0=%.2f Hz, 无量纲激励幅值 Ze_hat=%.4f', app.f0_val, app.Ze_hat_val));
        end

        % =================================================================
        % 几何机构拓扑位置可视化引擎 (新增并且严格封闭在 methods 块内)
        % =================================================================
        function plotMechanismGeometry(app, a, h1, h, h2)
            cla(app.AxGeom, 'reset');
            hold(app.AxGeom, 'on');
            grid(app.AxGeom, 'on');
            
            O = [0, 0];                  
            Top_Fix = [0, h1];           
            Bot_Fix = [0, -h1];          
            Left_Anchor1  = [-a,  (h2-h1)/2]; 
            Right_Anchor1 = [ a,  (h2-h1)/2];
            Left_Anchor2  = [-a, -(h2-h1)/2];
            Right_Anchor2 = [ a, -(h2-h1)/2];
            
            plot(app.AxGeom, [Left_Anchor1(1), Left_Anchor2(1)], [Left_Anchor1(2), Left_Anchor2(2)], 'k-', 'LineWidth', 4);
            plot(app.AxGeom, [Right_Anchor1(1), Right_Anchor2(1)], [Right_Anchor1(2), Right_Anchor2(2)], 'k-', 'LineWidth', 4);
            plot(app.AxGeom, Top_Fix(1), Top_Fix(2), 'ks', 'MarkerFaceColor', [0.3 0.3 0.3], 'MarkerSize', 10);
            plot(app.AxGeom, Bot_Fix(1), Bot_Fix(2), 'ks', 'MarkerFaceColor', [0.3 0.3 0.3], 'MarkerSize', 10);
            
            plot(app.AxGeom, [O(1), Top_Fix(1)], [O(2), Top_Fix(2)], 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 3, 'LineStyle', '-.', 'DisplayName', 'Vertical Springs (k_1)');
            plot(app.AxGeom, [O(1), Bot_Fix(1)], [O(2), Bot_Fix(2)], 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 3, 'LineStyle', '-.');
            
            plot(app.AxGeom, [O(1), Left_Anchor1(1)], [O(2), Left_Anchor1(2)], 'Color', [0 0.4470 0.7410], 'LineWidth', 3, 'DisplayName', 'Oblique Upper (k_3)');
            plot(app.AxGeom, [O(1), Right_Anchor1(1)], [O(2), Right_Anchor1(2)], 'Color', [0 0.4470 0.7410], 'LineWidth', 3);
            
            plot(app.AxGeom, [O(1), Left_Anchor2(1)], [O(2), Left_Anchor2(2)], 'Color', [0.4660 0.6740 0.1880], 'LineWidth', 3, 'DisplayName', 'Oblique Lower (k_2)');
            plot(app.AxGeom, [O(1), Right_Anchor2(1)], [O(2), Right_Anchor2(2)], 'Color', [0.4660 0.6740 0.1880], 'LineWidth', 3);
            
            plot(app.AxGeom, O(1), O(2), 'ko', 'MarkerFaceColor', 'y', 'MarkerSize', 18, 'DisplayName', 'Isolated Mass (M)');
            text(app.AxGeom, O(1)+5, O(2)+5, 'Mass M', 'FontWeight', 'bold', 'Color', 'k');
            
            text(app.AxGeom, -a/2, (h2-h1)/4 + 10, sprintf('a = %.1f mm', a), 'HorizontalAlignment', 'center');
            text(app.AxGeom, 10, h1/2, sprintf('h_1 = %.1f mm', h1), 'Color', [0.5 0.5 0.5]);
            
            title(app.AxGeom, 'QZS 隔振系统机构弹簧空间位置几何分布示意图', 'FontSize', 12);
            xlabel(app.AxGeom, '水平跨度方向 X (mm)'); ylabel(app.AxGeom, '垂直运动方向 Y (mm)');
            
            max_range = max([a, h1, h2]) * 1.2;
            app.AxGeom.XLim = [-max_range, max_range]; app.AxGeom.YLim = [-max_range, max_range];
            legend(app.AxGeom, 'Location', 'northeastoutside');
            hold(app.AxGeom, 'off');
        end

        % =================================================================
        % 外部双信号CSV载入及FFT解析
        % =================================================================
        function processVibrationSignals(app)
            [file1, path1] = uigetfile('*.csv', '第1步：选择【输入端信号】CSV'); if isequal(file1, 0), return; end
            [file2, path2] = uigetfile('*.csv', '第2步：选择【参考对照】CSV'); if isequal(file2, 0), return; end
            
            try
                app.addLog('>>> 正在导入数据并执行频域解算...');
                data_in = readmatrix(fullfile(path1, file1), 'NumHeaderLines', 3);
                app.t_matrix = data_in(:, 1); app.v_in_data = data_in(:, 2) / 100;
                app.v_in_data = app.v_in_data - mean(app.v_in_data);
                
                dt = app.t_matrix(2) - app.t_matrix(1); app.fs_rate = 1 / dt; app.N_points = length(app.v_in_data);
                n_pos = floor(app.N_points/2); freq_vec = (0:app.N_points-1) * app.fs_rate / app.N_points;
                freq_range = freq_vec(1:n_pos); Omega_range = freq_range / app.f0_val;
                
                app.v_out_matrix = zeros(app.N_points, 5);
                mu1_vals = [0.1907, 0.1188, 0.00048, 0.3367, 0.2189]; mu3_vals = [1.3836, 1.2344, 0.0017,  0.3876, 0.2104];
                
                for i = 1:5
                    Ta_curve = zeros(1, n_pos);
                    for j = 1:n_pos
                        Ta_curve(j) = app.compute_transmissibility(mu1_vals(i), mu3_vals(i), Omega_range(j), app.Ze_hat_val, app.zeta_val);
                    end
                    H_full = zeros(app.N_points, 1); H_full(1:n_pos) = Ta_curve;
                    H_full(app.N_points:-1:app.N_points-n_pos+2) = conj(Ta_curve(2:n_pos));
                    V_in_fft = fft(app.v_in_data); app.v_out_matrix(:, i) = real(ifft(V_in_fft(:) .* H_full));
                end
                
                data_ref = readmatrix(fullfile(path2, file2), 'NumHeaderLines', 3);
                t_ref = data_ref(:, 1); v_ref = data_ref(:, 2) / 100 - mean(data_ref(:, 2) / 100);
                fs_ref = 1 / (t_ref(2) - t_ref(1));
                
                win_sz = min(app.N_points, floor(1 * app.fs_rate)); nfft = 2^nextpow2(win_sz); ovlp = nfft/2;
                app.f_psd_vec = (0:nfft/2-1)*app.fs_rate/nfft; win = hann(win_sz); win = win ./ sqrt(mean(win.^2));
                
                app.v_in_psd_vec = app.compute_psd_internal(app.v_in_data, win_sz, ovlp, nfft, app.fs_rate, win);
                app.v_out_psd_matrix = zeros(length(app.f_psd_vec), 5);
                for i = 1:5
                    app.v_out_psd_matrix(:, i) = app.compute_psd_internal(app.v_out_matrix(:, i), win_sz, ovlp, nfft, app.fs_rate, win);
                end
                
                v_ref_psd = app.compute_psd_internal(v_ref, win_sz, ovlp, nfft, fs_ref, win);
                f_ref_psd = (0:nfft/2-1)*fs_ref/nfft;
                v_ref_psd_interp = interp1(f_ref_psd, sqrt(v_ref_psd), app.f_psd_vec, 'linear', 'extrap');
                
                app.drawTimeAndPSDTabs(v_ref_psd_interp);
            catch ME
                app.addLog(['解算中断: ' ME.message]);
            end
        end

        % =================================================================
        % 时频两域画布渲染
        % =================================================================
        function drawTimeAndPSDTabs(app, v_ref_psd_interp)
            delete(app.Tab4.Children); 
            colors_map = {[0 0.4470 0.7410], [0.8500 0.3250 0.0980], [0.4660 0.6740 0.1880], [0.4940 0.1840 0.5560], [0.3010 0.7450 0.9330]};
            time_show = min(2, app.t_matrix(end)); idx_show = app.t_matrix <= time_show;
            
            positions = {[50, 480, 360, 180], [460, 480, 360, 180]; [50, 260, 360, 180], [460, 260, 360, 180]; [50,  40, 360, 180], [460,  40, 360, 180]};
            
            ax_in = uiaxes(app.Tab4, 'Position', positions{1,1});
            plot(ax_in, app.t_matrix(idx_show), app.v_in_data(idx_show), '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 2);
            title(ax_in, 'Input Signal'); grid(ax_in, 'on'); ax_in.XLim = [0, time_show];
            
            for i = 1:5
                row = floor(i/2) + 1; col = mod(i,2) + 1; if col == 1, row = row - 1; col = 2; end
                ax_out = uiaxes(app.Tab4, 'Position', positions{row, col});
                plot(ax_out, app.t_matrix(idx_show), app.v_out_matrix(idx_show, i), 'Color', colors_map{i}, 'LineWidth', 1.5);
                title(ax_out, sprintf('Output Response %d', i)); grid(ax_out, 'on'); ax_out.XLim = [0, time_show];
            end
            
            cla(app.Ax5); hold(app.Ax5, 'on');
            h_in = loglog(app.Ax5, app.f_psd_vec, sqrt(app.v_in_psd_vec), '--', 'Color', [0.5, 0.5, 0.5], 'LineWidth', 2.5, 'DisplayName', 'Input Signal');
            h_outs = zeros(1, 5);
            param_legends = {'Group1: δ̂=0.500', 'Group2: δ̂=0.471', 'Group3: δ̂=0.800', 'Group4: δ̂=0.500', 'Group5: δ̂=0.200'};
            for i = 1:5
                h_outs(i) = loglog(app.Ax5, app.f_psd_vec, sqrt(app.v_out_psd_matrix(:, i)), 'Color', colors_map{i}, 'LineWidth', 2, 'DisplayName', param_legends{i});
            end
            h_ref = loglog(app.Ax5, app.f_psd_vec, v_ref_psd_interp, 'k-', 'LineWidth', 2.5, 'DisplayName', 'Reference Curve');
            xlabel(app.Ax5, 'Frequency (Hz)'); ylabel(app.Ax5, 'PSD [V/\sqrt{Hz}]');
            title(app.Ax5, 'Power Spectrum Density Comparison'); app.Ax5.XLim = [0.5, app.fs_rate/2]; grid(app.Ax5, 'on');
            legend(app.Ax5, [h_in, h_outs, h_ref], 'Location', 'southwest', 'FontSize', 8); hold(app.Ax5, 'off');
            app.addLog('>>> 时频域高阶解算完成。');
        end

        % =================================================================
        % 基础底层数学工具
        % =================================================================
        function Ta = compute_transmissibility(~, mu1_tgt, mu3_tgt, Omega, Ze_h, zta)
            if Omega < 1e-6, Ta = 1; return; end
            a = (9/16) * mu3_tgt^2 * Ze_h^4; b = 1.5 * mu3_tgt * (mu1_tgt - Omega^2) * Ze_h^2; c = (mu1_tgt - Omega^2)^2 + (2*zta*Omega)^2; d = -Omega^4;
            roots_Z2 = roots([a, b, c, d]); Z2_candidates = roots_Z2(abs(imag(roots_Z2)) < 1e-6 & real(roots_Z2) > 0);
            if isempty(Z2_candidates), Z_linear = Omega^2 / sqrt((mu1_tgt - Omega^2)^2 + (2*zta*Omega)^2); Z2 = Z_linear^2; else Z2 = min(real(Z2_candidates)); end
            Z_hat = sqrt(Z2);
            cos_phi = (0.75 * mu3_tgt * Ze_h^2 * Z_hat^3 + (mu1_tgt - Omega^2) * Z_hat) / Omega^2; cos_phi = max(-1, min(1, cos_phi));
            Ta = sqrt(1 + 2 * Z_hat * cos_phi + Z_hat^2);
        end

        function psd = compute_psd_internal(~, signal, win_sz, ovlp, nfft, fs, win)
            signal = signal(:); data_frames = buffer(signal, win_sz, ovlp, 'nodelay');
            if size(data_frames, 1) < win_sz, data_frames = data_frames(:, 1:end-1); end
            data_windowed = data_frames .* win; fft_data = fft(data_windowed, nfft);
            psd_matrix = (abs(fft_data(1:nfft/2, :)).^2) / (fs * nfft); psd_matrix(2:end-1, :) = 2 * psd_matrix(2:end-1, :);
            psd = mean(psd_matrix, 2);
        end

        function addLog(app, txt)
            app.LogTextArea.Value = [app.LogTextArea.Value; {txt}]; scroll(app.LogTextArea, 'bottom');
        end
    end
end