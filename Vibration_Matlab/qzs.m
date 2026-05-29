classdef QZS_App < matlab.apps.AppBase

    % --- 界面组件属性声明 ---
    properties (Access = public)
        UIWindow               matlab.ui.Figure
        LeftPanel              matlab.ui.container.Panel
        RightTabGroup          matlab.ui.container.TabGroup
        
        % 标签页按新顺序排列（几何配置放最前）
        TabGeom, Tab1, Tab3, Tab4, Tab5
        
        % 图像坐标轴句柄
        AxGeom, Ax1, Ax3, Ax3_Inset, Ax4, Ax5
        
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
    
    % --- 内部核心数据属性（去除了5组多余矩阵） ---
    properties (Access = private)
        y_hat                  double % 无量纲位移采样点
        f0_val                 double % 固有频率
        Ze_hat_val             double % 无量纲激励幅值
        zeta_val               double % 阻尼比
        
        % 外部信号数据容器
        t_matrix, v_in_data, fs_rate, N_points
        v_out_data, f_psd_vec, v_in_psd_vec, v_out_psd_vec
    end

    % --- 构造函数与私有数据初始化 ---
    methods (Access = public)
        function app = QZS_App()
            app.createComponents();
            
            % 初始化无量纲位移区间
            app.y_hat = linspace(-10, 10, 1000);
                
            app.UIWindow.Visible = 'on';
            app.addLog('系统就绪。请配置参数后点击“运行刚度匹配并导出Excel”按钮。');
        end
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
            
            % 右侧标签页组 (更改顺序：几何配置图调整至第 1 个)
            app.RightTabGroup = uitabgroup(app.UIWindow, 'Position', [360 10 880 800]);
            app.TabGeom = uitab(app.RightTabGroup, 'Title', '1. 机构几何装配图');
            app.Tab1    = uitab(app.RightTabGroup, 'Title', '2. 无量纲力/刚度曲线');
            app.Tab3    = uitab(app.RightTabGroup, 'Title', '3. 位移传递率分析');
            app.Tab4    = uitab(app.RightTabGroup, 'Title', '4. 时域电压响应');
            app.Tab5    = uitab(app.RightTabGroup, 'Title', '5. 功率谱密度PSD对比');
            
            % 初始化各坐标轴
            app.AxGeom    = uiaxes(app.TabGeom, 'Position', [60 80 760 640]);
            app.Ax1       = uiaxes(app.Tab1, 'Position', [60 80 760 640]);
            app.Ax3       = uiaxes(app.Tab3, 'Position', [60 80 760 640]);
            app.Ax3_Inset = uiaxes(app.Tab3, 'Position', [540 380 240 240]); 
            app.Ax4       = uiaxes(app.Tab4, 'Position', [40 40 800 680]); 
            app.Ax5       = uiaxes(app.Tab5, 'Position', [60 80 760 640]);
        end
    end
    methods (Access = private)
        % =================================================================
        % 核心算法内核：物理弹簧及结构尺寸逆解 + Excel导出
        % =================================================================
        function calculateAndExportSprings(app)
            app.LogTextArea.Value = ""; 
            app.addLog('>>> 开始根据目标无量纲参数反求物理弹簧及结构尺寸...');
            
            % 1. 读取界面参数
            d_hat = app.DeltaHatEdit.Value;  a_hat = app.AHatEdit.Value;
            alpha = app.AlphaEdit.Value;     alpha1 = app.Alpha1Edit.Value;
            gamma = app.GammaEdit.Value;     a_tgt = app.ATargetEdit.Value;
            tau_p = app.TauPEdit.Value;      G = app.GEdit.Value;
            g = 9.81;
            
            % 2. 几何原长与预压缩量推导
            h1_tgt = sqrt(a_tgt^2 * (1/a_hat^2 - 1));
            delta_tgt = d_hat * sqrt(a_tgt^2 + h1_tgt^2);
            L1 = sqrt(a_tgt^2 + h1_tgt^2) + delta_tgt;
            
            d_tgt_geom = h1_tgt / (gamma - 1);
            h_tgt = h1_tgt + d_tgt_geom;
            h2_tgt = h1_tgt + 2*d_tgt_geom;
            
            rho_tgt = (1 - a_hat^2) / (gamma - 1)^2;
            d_hat1_tgt = 1 - sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho_tgt) + rho_tgt) + d_hat;
            d_hat2_tgt = 1 - sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_tgt) + 4*rho_tgt) + d_hat;
            delta1_tgt = d_hat1_tgt * sqrt(a_tgt^2 + h1_tgt^2);
            delta2_tgt = d_hat2_tgt * sqrt(a_tgt^2 + h1_tgt^2);
            
            L2 = sqrt(a_tgt^2 + h_tgt^2) + delta1_tgt;
            L3 = sqrt(a_tgt^2 + h2_tgt^2) + delta2_tgt;
            
            % 3. 标准弹簧刚度基准求解(按内置选型数据推算)
            k2_base = (G * 1.2^4) / (8 * 15.6^3 * 14) * 1000; 
            M_computed = (k2_base * 1.229 * sqrt((a_tgt/1000)^2 + (h1_tgt/1000)^2)) / g;
            app.addLog(sprintf('结构计算：h1=%.1fmm, 自动匹配负载 M=%.2f kg', h1_tgt, M_computed));
            
            % 4. 平衡压缩量推导
            k1_base = k2_base * alpha;   k3_base = k2_base * alpha1;
            f1 = -(k1_base/1000)*delta_tgt*(h1_tgt/sqrt(a_tgt^2+h1_tgt^2));
            f3 = -(k3_base/1000)*delta1_tgt*(h_tgt/sqrt(a_tgt^2+h_tgt^2));
            f4 = -(k1_base/1000)*delta2_tgt*(h2_tgt/sqrt(a_tgt^2+h2_tgt^2));
            f2 = -(2*f1 + 2*f3 + 2*f4);
            L = h2_tgt + f2 / (k2_base/1000);
            
            % 5. 循环迭代生成弹簧推荐表
            C_range = 5:1:12;  ratio_range = 0.28:0.01:0.5;
            
            k2_tab = app.iterSpringData(C_range, ratio_range, G, L, k2_base, M_computed, g, tau_p);
            k1_tab = app.iterSpringData(C_range, ratio_range, G, L1, k1_base, M_computed, g, tau_p);
            k3_tab = app.iterSpringData(C_range, ratio_range, G, L2, k3_base, M_computed, g, tau_p);

            try
                excel_filename = fullfile(app.ExcelPathEdit.Value, 'Spring_Parameters.xlsx');
                writetable(k2_tab, excel_filename, 'Sheet', 'K2_Spring');
                writetable(k1_tab, excel_filename, 'Sheet', 'Up_Down_Spring');
                writetable(k3_tab, excel_filename, 'Sheet', 'Middle_Spring');
                app.addLog(['成功导出弹簧参数表至：', excel_filename]);
            catch ME
                app.addLog(['Excel导出失败: ', ME.message]);
            end
            
            % 6. 核心物理量固化
            app.f0_val = (sqrt(k2_base/M_computed)) / (2*pi);
            app.Ze_hat_val = (app.ZeEdit.Value / 1000) / sqrt((a_tgt/1000)^2 + (h1_tgt/1000)^2);
            app.zeta_val = app.CEdit.Value * (sqrt(k2_base/M_computed)) / (2 * k2_base);

            % 7. 触发图形绘制
            app.plotMechanismGeometry(a_tgt, h1_tgt, h_tgt, h2_tgt); 
            app.plotStaticCurves(rho_tgt, d_hat, d_hat1_tgt, d_hat2_tgt, alpha, alpha1);
            app.plotTransmissibility();
        end
        
        % 弹簧选型数据表循环生成工具
        function res_table = iterSpringData(~, C_rng, r_rng, G, Length, k_base, M, g, tau_p)
            results = [];
            for C = C_rng
                for ratio = r_rng
                    a_coef = (G*ratio)/(8*(C^4)*(k_base/1000));
                    D_val = (-2/C + sqrt(4/(C^2) + 4*a_coef*Length)) / (2*a_coef);
                    d_val = D_val / C;
                    K_factor = (4*C-1)/(4*C-4) + 0.615/C;
                    d_tgt = 1.6*sqrt(K_factor*C*M*g/tau_p);
                    n_val = (G*D_val) / (8*(C^4)*(k_base/1000));
                    k_act = (G*D_val) / (8*(C^4)*n_val);
                    results = [results; d_tgt, d_val, D_val, D_val+d_val, C, n_val, ratio, ratio*D_val, G, Length, k_act*1000];
                end
            end
            res_table = array2table(results, 'VariableNames', {'d_target_mm', 'd_mm', 'D_mm','D_out_mm','C', 'n', 'ratio', 'p_mm', 'G_Mpa', 'L_mm', 'k_actual_N_m'});
            [~, ia] = unique(res_table(:, {'C', 'ratio'}), 'rows'); res_table = res_table(ia, :);
        end
        % =================================================================
        % 1. 机构几何装配图渲染（已放至最前）
        % =================================================================
        function plotMechanismGeometry(app, a, h1, h, h2)
            cla(app.AxGeom, 'reset'); hold(app.AxGeom, 'on'); grid(app.AxGeom, 'on');
            
            O = [0, 0]; Top_Fix = [0, h1]; Bot_Fix = [0, -h1];          
            L_Anch1  = [-a, (h2-h1)/2];  R_Anch1 = [ a, (h2-h1)/2];
            L_Anch2  = [-a, -(h2-h1)/2]; R_Anch2 = [ a, -(h2-h1)/2];
            
            % 绘制支架固定壁面线
            plot(app.AxGeom, [L_Anch1(1), L_Anch2(1)], [L_Anch1(2), L_Anch2(2)], 'k-', 'LineWidth', 4);
            plot(app.AxGeom, [R_Anch1(1), R_Anch2(1)], [R_Anch1(2), R_Anch2(2)], 'k-', 'LineWidth', 4);
            plot(app.AxGeom, [Top_Fix(1), Bot_Fix(1)], [Top_Fix(2), Bot_Fix(2)], 'k--', 'LineWidth', 1);
            
            % 绘制各组弹簧代表线段
            plot(app.AxGeom, [O(1), Top_Fix(1)], [O(2), Top_Fix(2)], 'Color', [0.85 0.32 0.1], 'LineWidth', 3, 'LineStyle', '-.', 'DisplayName', 'Vertical Springs (k_1)');
            plot(app.AxGeom, [O(1), Bot_Fix(1)], [O(2), Bot_Fix(2)], 'Color', [0.85 0.32 0.1], 'LineWidth', 3, 'LineStyle', '-.');
            plot(app.AxGeom, [O(1), L_Anch1(1)], [O(2), L_Anch1(2)], 'Color', [0 0.44 0.74], 'LineWidth', 3, 'DisplayName', 'Oblique Upper (k_3)');
            plot(app.AxGeom, [O(1), R_Anch1(1)], [O(2), R_Anch1(2)], 'Color', [0 0.44 0.74], 'LineWidth', 3);
            plot(app.AxGeom, [O(1), L_Anch2(1)], [O(2), L_Anch2(2)], 'Color', [0.46 0.67 0.18], 'LineWidth', 3, 'DisplayName', 'Oblique Lower (k_2)');
            plot(app.AxGeom, [O(1), R_Anch2(1)], [O(2), R_Anch2(2)], 'Color', [0.46 0.67 0.18], 'LineWidth', 3);
            
            % 隔离质量块中心
            plot(app.AxGeom, O(1), O(2), 'ko', 'MarkerFaceColor', 'y', 'MarkerSize', 18, 'DisplayName', 'Isolated Mass (M)');
            text(app.AxGeom, O(1)+5, O(2)+5, 'Mass M', 'FontWeight', 'bold');
            
            title(app.AxGeom, 'QZS 隔振系统机构弹簧空间位置几何分布示意图', 'FontSize', 12);
            xlabel(app.AxGeom, '水平跨度方向 X (mm)'); ylabel(app.AxGeom, '垂直运动方向 Y (mm)');
            max_range = max([a, h1, h2]) * 1.2;
            app.AxGeom.XLim = [-max_range, max_range]; app.AxGeom.YLim = [-max_range, max_range];
            legend(app.AxGeom, 'Location', 'northeastoutside'); hold(app.AxGeom, 'off');
        end

        % =================================================================
        % 2. 无量纲回复力与刚度曲线单线绘制
        % =================================================================
        function plotStaticCurves(app, rho_t, d_hat, d_hat1_t, d_hat2_t, alpha, alpha1)
            cla(app.Ax1, 'reset');
            x_e_hat = sqrt(1 - app.AHatEdit.Value^2) + sqrt(rho_t);
            K_hat = zeros(size(app.y_hat)); f_hat = zeros(size(app.y_hat)); y_hat_vec = zeros(size(app.y_hat));
            
            for i = 1:length(app.y_hat)
                xi_h = x_e_hat + app.y_hat(i);
                P1 = sqrt(1 - app.AHatEdit.Value^2) - xi_h;              P2 = 1 - 2*sqrt(1 - app.AHatEdit.Value^2)*xi_h + xi_h^2; P3 = 1 + d_hat;
                P4 = sqrt(1 - app.AHatEdit.Value^2 + rho_t + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t)) - xi_h;
                P5 = 1 + rho_t + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t) - 2*sqrt(1 - app.AHatEdit.Value^2 + rho_t + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t))*xi_h + xi_h^2;
                P6 = sqrt(1 + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t) + rho_t) + d_hat1_t;
                P7 = sqrt(1 - app.AHatEdit.Value^2) + 2*sqrt(rho_t) - xi_h;
                P8 = 1 + 4*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t) + 4*rho_t - 2*(sqrt(1 - app.AHatEdit.Value^2) + 2*sqrt(rho_t))*xi_h + xi_h^2;
                P9 = sqrt(1 + 4*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t) + 4*rho_t) + d_hat2_t;
                
                dP2 = -2*sqrt(1 - app.AHatEdit.Value^2) + 2*xi_h;
                dP5 = -2*sqrt(1 - app.AHatEdit.Value^2 + rho_t + 2*sqrt(1 - app.AHatEdit.Value^2)*sqrt(rho_t)) + 2*xi_h;
                dP8 = -2*(sqrt(1 - app.AHatEdit.Value^2) + 2*sqrt(rho_t)) + 2*xi_h;
                
                dN1 = -2 * alpha * (1 - P3 * P2^(-0.5)) * (-1) - alpha * P1 * P2^(-1.5) * P3 * dP2;
                dN3 = -2 * alpha1 * (1 - P6 * P5^(-0.5)) * (-1) - alpha1 * P4 * P5^(-1.5) * P6 * dP5;
                dN5 = -2 * alpha * (1 - P9 * P8^(-0.5)) * (-1) - alpha * P7 * P8^(-1.5) * P9 * dP8;
                
                K_hat(i) = 1 + dN1 + dN3 + dN5;
                f_hat(i) = xi_h - 2*alpha * P1*(sqrt(P2)-P3)/sqrt(P2) - 2*alpha1 * P4*(sqrt(P5)-P6)/sqrt(P5) - 2*alpha * P7*(sqrt(P8)-P9)/sqrt(P8);
                y_hat_vec(i) = xi_h - x_e_hat;
            end
            
            yyaxis(app.Ax1, 'left');
            plot(app.Ax1, y_hat_vec, f_hat, 'Color', [0, 0.45, 0.74], 'LineWidth', 2.5);
            ylabel(app.Ax1, 'Dimensionless Force \bf\hat{f}'); app.Ax1.YLim = [-6, 6]; app.Ax1.XLim = [-3, 3];
            
            yyaxis(app.Ax1, 'right');
            plot(app.Ax1, y_hat_vec, K_hat, 'Color', [0.85, 0.32, 0.1], 'LineStyle', '--', 'LineWidth', 2.5);
            ylabel(app.Ax1, 'Dimensionless Stiffness \bf\hat{K}');
            
            grid(app.Ax1, 'on'); xlabel(app.Ax1, 'Dimensionless Displacement \bf\hat{y}');
            title(app.Ax1, 'Dimensionless Force and Stiffness Curves (Target Parameters)');
        end

        % =================================================================
        % 3. 目标参数传递率曲线单线化展示
        % =================================================================
        function plotTransmissibility(app)
            cla(app.Ax3); hold(app.Ax3, 'on'); grid(app.Ax3, 'on');
            cla(app.Ax3_Inset); hold(app.Ax3_Inset, 'on'); grid(app.Ax3_Inset, 'on');
            
            % 使用当前设置的目标物理参数代入非线性传递率解析方程
            mu1_tgt = 0.1907; mu3_tgt = 1.3836; 
            f_ex = linspace(0.1, 10, 1000); f_inset = linspace(6, 10, 200);
            
            Ta_main = zeros(size(f_ex)); Ta_ins = zeros(size(f_inset));
            for j = 1:length(f_ex)
                Omega = f_ex(j) / app.f0_val; 
                Ta_main(j) = app.compute_transmissibility(mu1_tgt, mu3_tgt, Omega, app.Ze_hat_val, app.zeta_val);
            end
            for j = 1:length(f_inset)
                Omega = f_inset(j) / app.f0_val; 
                Ta_ins(j) = app.compute_transmissibility(mu1_tgt, mu3_tgt, Omega, app.Ze_hat_val, app.zeta_val);
            end
            
            % 仅保留一条核心目标参数对应的曲线表现
            plot(app.Ax3, f_ex, Ta_main, 'Color', [0 0.44 0.74], 'LineWidth', 2.5, 'DisplayName', 'Target System');
            plot(app.Ax3_Inset, f_inset, Ta_ins, 'Color', [0 0.44 0.74], 'LineWidth', 1.5);
            
            yline(app.Ax3, 1, 'k--', 'LineWidth', 1.2, 'HandleVisibility', 'off');
            app.Ax3.XLim = [0, 10]; app.Ax3.YLim = [0, 10];
            xlabel(app.Ax3, 'Frequency (Hz)'); ylabel(app.Ax3, 'Transmissibility T_a');
            title(app.Ax3, sprintf('Target Displacement Transmissibility (\\zeta = %.3f)', app.zeta_val));
            app.Ax3_Inset.XLim = [6, 10]; app.Ax3_Inset.YLim = [0, 0.25];
            hold(app.Ax3, 'off'); hold(app.Ax3_Inset, 'off');
            
            app.addLog(sprintf('理论计算匹配就绪：系统特征频 f0=%.2f Hz, 无量纲激励幅 Ze_hat=%.4f', app.f0_val, app.Ze_hat_val));
        end

        % =================================================================
        % 4. 外部双信号信号时频域解算（清理了5组多通道循环，解算提速）
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
                
                % 仅计算目标单一响应
                mu1_tgt = 0.1907; mu3_tgt = 1.3836;
                Ta_curve = zeros(1, n_pos);
                for j = 1:n_pos
                    Ta_curve(j) = app.compute_transmissibility(mu1_tgt, mu3_tgt, Omega_range(j), app.Ze_hat_val, app.zeta_val);
                end
                H_full = zeros(app.N_points, 1); H_full(1:n_pos) = Ta_curve;
                H_full(app.N_points:-1:app.N_points-n_pos+2) = conj(Ta_curve(2:n_pos));
                V_in_fft = fft(app.v_in_data); app.v_out_data = real(ifft(V_in_fft(:) .* H_full));
                
                % 载入参考对比数据
                data_ref = readmatrix(fullfile(path2, file2), 'NumHeaderLines', 3);
                t_ref = data_ref(:, 1); v_ref = data_ref(:, 2) / 100 - mean(data_ref(:, 2) / 100);
                fs_ref = 1 / (t_ref(2) - t_ref(1));
                
                % 窗函数与功率谱密度
                win_sz = min(app.N_points, floor(1 * app.fs_rate)); nfft = 2^nextpow2(win_sz); ovlp = nfft/2;
                app.f_psd_vec = (0:nfft/2-1)*app.fs_rate/nfft; win = hann(win_sz); win = win ./ sqrt(mean(win.^2));
                
                app.v_in_psd_vec = app.compute_psd_internal(app.v_in_data, win_sz, ovlp, nfft, app.fs_rate, win);
                app.v_out_psd_vec = app.compute_psd_internal(app.v_out_data, win_sz, ovlp, nfft, app.fs_rate, win);
                
                v_ref_psd = app.compute_psd_internal(v_ref, win_sz, ovlp, nfft, fs_ref, win);
                f_ref_psd = (0:nfft/2-1)*fs_ref/nfft;
                v_ref_psd_interp = interp1(f_ref_psd, sqrt(v_ref_psd), app.f_psd_vec, 'linear', 'extrap');
                
                app.drawTimeAndPSDTabs(v_ref_psd_interp);
            catch ME
                app.addLog(['解算中断: ' ME.message]);
            end
        end

        % =================================================================
        % 5. 简化版画布渲染展示（时域改为Input与Output双画布比对，信息更集中）
        % =================================================================
        function drawTimeAndPSDTabs(app, v_ref_psd_interp)
            delete(app.Tab4.Children); 
            time_show = min(2, app.t_matrix(end)); idx_show = app.t_matrix <= time_show;
            
            % 左画布：输入端
            ax_in = uiaxes(app.Tab4, 'Position', [50, 240, 360, 300]);
            plot(ax_in, app.t_matrix(idx_show), app.v_in_data(idx_show), 'Color', [0.5 0.5 0.5], 'LineWidth', 2);
            title(ax_in, 'Input Base Signal Waveform'); grid(ax_in, 'on'); ax_in.XLim = [0, time_show];
            
            % 右画布：经QZS系统衰减后的输出端
            ax_out = uiaxes(app.Tab4, 'Position', [450, 240, 360, 300]);
            plot(ax_out, app.t_matrix(idx_show), app.v_out_data(idx_show), 'Color', [0 0.44 0.74], 'LineWidth', 2);
            title(ax_out, 'Output Isolated Response'); grid(ax_out, 'on'); ax_out.XLim = [0, time_show];
            
            % 功率谱密度图谱绘制
            cla(app.Ax5); hold(app.Ax5, 'on');
            loglog(app.Ax5, app.f_psd_vec, sqrt(app.v_in_psd_vec), '--', 'Color', [0.5 0.5 0.5], 'LineWidth', 2, 'DisplayName', 'Input Base');
            loglog(app.Ax5, app.f_psd_vec, sqrt(app.v_out_psd_vec), 'Color', [0 0.44 0.74], 'LineWidth', 2.5, 'DisplayName', 'Output QZS Target');
            loglog(app.Ax5, app.f_psd_vec, v_ref_psd_interp, 'k:', 'LineWidth', 2, 'DisplayName', 'Reference Standard');
            
            xlabel(app.Ax5, 'Frequency (Hz)'); ylabel(app.Ax5, 'PSD [V/\sqrt{Hz}]');
            title(app.Ax5, 'Power Spectrum Density Comparison'); app.Ax5.XLim = [0.5, app.fs_rate/2]; grid(app.Ax5, 'on');
            legend(app.Ax5, 'Location', 'southwest'); hold(app.Ax5, 'off');
            app.addLog('>>> 时频域解算与绘图渲染完成。');
        end

        % =================================================================
        % 底层复数代数根工具
        % =================================================================
        function Ta = compute_transmissibility(~, mu1, mu3, Omega, Ze_h, zta)
            if Omega < 1e-6, Ta = 1; return; end
            a = (9/16) * mu3^2 * Ze_h^4; b = 1.5 * mu3 * (mu1 - Omega^2) * Ze_h^2; 
            c = (mu1 - Omega^2)^2 + (2*zta*Omega)^2; d = -Omega^4;
            roots_Z2 = roots([a, b, c, d]); Z2_candidates = roots_Z2(abs(imag(roots_Z2)) < 1e-6 & real(roots_Z2) > 0);
            if isempty(Z2_candidates)
                Z2 = (Omega^2 / sqrt((mu1 - Omega^2)^2 + (2*zta*Omega)^2))^2; 
            else 
                Z2 = min(real(Z2_candidates)); 
            end
            Z_hat = sqrt(Z2);
            cos_phi = (0.75 * mu3 * Ze_h^2 * Z_hat^3 + (mu1 - Omega^2) * Z_hat) / Omega^2; 
            cos_phi = max(-1, min(1, cos_phi));
            Ta = sqrt(1 + 2 * Z_hat * cos_phi + Z_hat^2);
        end

        function psd = compute_psd_internal(~, signal, win_sz, ovlp, nfft, fs, win)
            signal = signal(:); data_frames = buffer(signal, win_sz, ovlp, 'nodelay');
            if size(data_frames, 1) < win_sz, data_frames = data_frames(:, 1:end-1); end
            fft_data = fft(data_frames .* win, nfft);
            psd_matrix = (abs(fft_data(1:nfft/2, :)).^2) / (fs * nfft); 
            psd_matrix(2:end-1, :) = 2 * psd_matrix(2:end-1, :);
            psd = mean(psd_matrix, 2);
        end

        function addLog(app, txt)
            app.LogTextArea.Value = [app.LogTextArea.Value; {txt}]; scroll(app.LogTextArea, 'bottom');
        end
    end
end