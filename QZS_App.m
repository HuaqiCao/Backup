classdef QZS_App < matlab.apps.AppBase

    % --- UI 界面组件属性声明 ---
    properties (Access = public)
        UIWindow               matlab.ui.Figure              % 主窗口句柄
        LeftPanel              matlab.ui.container.Panel     % 左侧配置控制面板
        RightAxesPanel         matlab.ui.container.Panel     % 右侧综合图表大面板

        % 各坐标轴句柄
        AxGeom                 matlab.ui.control.UIAxes      % 3D 机械结构拓扑图
        Ax1                    matlab.ui.control.UIAxes      % 无量纲力与刚度曲线
        Ax3                    matlab.ui.control.UIAxes      % 位移传递率分析图
        Ax3_Inset              matlab.ui.control.UIAxes      % 传递率低频放大内嵌图
        Ax4                    matlab.ui.control.UIAxes      % 时域振动响应曲线
        Ax5                    matlab.ui.control.UIAxes      % 频域功率谱密度(PSD)对比图

        % 理论隔振系统物理参数输入框
        DeltaHatEdit          matlab.ui.control.NumericEditField  % 无量纲预压缩量 delta_hat
        AHatEdit              matlab.ui.control.NumericEditField  % 无量纲几何结构比 a_hat
        AlphaEdit             matlab.ui.control.NumericEditField  % 刚度比系数 alpha
        Alpha1Edit            matlab.ui.control.NumericEditField  % 辅助参数 alpha1
        GammaEdit             matlab.ui.control.NumericEditField  % 非线性系数 gamma
        ATargetEdit           matlab.ui.control.NumericEditField  % 弹簧水平安装总跨度 a
        TauPEdit              matlab.ui.control.NumericEditField  % 剪切常数 tau_p
        GEdit                 matlab.ui.control.NumericEditField  % 剪切模量 G
        CEdit                 matlab.ui.control.NumericEditField  % 阻尼系数 c
        ZeEdit                matlab.ui.control.NumericEditField  % 基础激振幅值 Ze mm

        % 1. 底部弹簧 (Bottom)
        B_TurnsEdit, B_WireDiaEdit, B_CylinderEdit
        % 2. 上侧斜弹簧 (Upper)
        U_TurnsEdit, U_WireDiaEdit, U_CylinderEdit
        % 3. 中间斜弹簧 (Mid)
        M_TurnsEdit, M_WireDiaEdit, M_CylinderEdit
        % 4. 下侧斜弹簧 (Down)
        D_TurnsEdit, D_WireDiaEdit, D_CylinderEdit

        % 输入框句柄
        BaseThickEdit         matlab.ui.control.NumericEditField
        H4Edit                matlab.ui.control.NumericEditField
        H5Edit                matlab.ui.control.NumericEditField

        % 交互控制按钮与系统日志
        LoadCSVButton         matlab.ui.control.Button            % 载入并解算外部信号按钮
        DesignButton          matlab.ui.control.Button            % 绿色保存按钮
        LogTextArea           matlab.ui.control.TextArea          % 日志信息显示文本框
    end

    % --- 全局字体与图形控制常量 ---
    properties (Access = private, Constant)
        TitleFontSize = 22;       % 图表标题字号大小
        LabelFontSize = 20;       % 坐标轴标签字号大小
        TickFontSize  = 18;       % 坐标轴刻度数字号大小
        LegendFontSize = 12;      % 图例字号大小
    end

    % --- 内部核心数据与自适应几何控制变量 ---
    properties (Access = private)
        % 动力学求解中间变量
        y_hat, test_params
        f0_val, Ze_hat_val, zeta_val

        % 存储理论分析参考曲线缓存
        y_hat_curve, f_hat_theory, K_hat_theory
        % 存储实际调节后的实体响应数据缓存
        f_hat_actual, K_hat_actual

        % 外部振动信号与时频域数据缓存
        v_in_data, t_matrix, fs_rate, N_points
        v_out_matrix, f_psd_vec, v_in_psd_vec, v_out_psd_matrix
        v_out_data

        % 立体弹簧独立几何尺寸
        k_vert, L0_vert, d_vert, D_vert, n_vert
        k_upper, L0_upper, d_upper, D_upper, n_upper
        k_mid,   L0_mid,   d_mid,   D_mid,   n_mid
        k_lower, L0_lower, d_lower, D_lower, n_lower

        % 3D 几何构型结构参数
        a1 = 30;       % 中间滑动滑动平台物理宽度 (mm)
        h3 = 90.0;     % 中间滑动滑动平台物理高度 (mm)
        platform_d = 20.0;       % 中间滑动滑动平台物理厚度 (mm)
        h4 = 20.0;     % 滑动平台上 3 组弹簧端点的垂直间距
        h5 = 48.0;     % 外部支架立柱上弹簧固定端的垂直间距
        a = 60.0;      % 弹簧水平安装总跨度
        base_thickness = 5.0;    % 底部地基基座厚度 (mm)
        column_thickness = 15.0; % 左右固定支架的显示粗细 (LineWidth)
    end

    % --- 核心生命周期与构造函数 ---
    methods (Access = public)
        function app = QZS_App()
            createComponents(app);
            registerApp(app, app.UIWindow);
            calculateAndPlotWorkflow(app);
        end

        function delete(app)
            delete(app.UIWindow);
        end
    end

    methods (Access = private)

        % --- 前端 UI 界面组件布局构建 ---
        function createComponents(app)
            app.UIWindow = uifigure('Name', 'QZS Nonlinear Isolation System Pro', 'Position', [50 50 1420 850]);

            app.LeftPanel = uipanel(app.UIWindow, 'Title', 'Configuration', 'Position', [10 10 190 830], 'FontWeight', 'bold');

            y_pos = 785;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'delta_hat (δ̂):', 'FontSize', 14, 'FontWeight', 'bold');
            app.DeltaHatEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', 0.5, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.leftFieldValueChanged(edf, 'delta_hat'));

            y_pos = y_pos - 32;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'a_hat (â):', 'FontSize', 14, 'FontWeight', 'bold');
            app.AHatEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', 0.755, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.leftFieldValueChanged(edf, 'a_hat'));

            y_pos = y_pos - 32;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'alpha (α):', 'FontSize', 14, 'FontWeight', 'bold');
            app.AlphaEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', 0.942, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.leftFieldValueChanged(edf, 'alpha'));

            y_pos = y_pos - 32;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'alpha1 (α₁):', 'FontSize', 14, 'FontWeight', 'bold');
            app.Alpha1Edit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', 0.501, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.leftFieldValueChanged(edf, 'alpha1'));

            y_pos = y_pos - 32;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'gamma (γ):', 'FontSize', 14, 'FontWeight', 'bold');
            app.GammaEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', 2.143, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.leftFieldValueChanged(edf, 'gamma'));

            y_pos = y_pos - 32;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'a (mm):', 'FontSize', 14, 'FontWeight', 'bold');
            app.ATargetEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', app.a, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.updateGeometrySpan());

            y_pos = y_pos - 32;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'tau_p (Mpa):', 'FontSize', 14, 'FontWeight', 'bold');
            app.TauPEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', 70.0, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.calculateAndPlotWorkflow());

            y_pos = y_pos - 32;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'G (MPa):', 'FontSize', 14, 'FontWeight', 'bold');
            app.GEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', 75000, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.calculateAndPlotWorkflow());

            y_pos = y_pos - 32;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'Damping C:', 'FontSize', 14, 'FontWeight', 'bold');
            app.CEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', 20, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.calculateAndPlotWorkflow());

            y_pos = y_pos - 32;
            uilabel(app.LeftPanel, 'Position', [5 y_pos 95 22], 'Text', 'Ze (mm):', 'FontSize', 14, 'FontWeight', 'bold');
            app.ZeEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [105 y_pos 70 24], 'Value', 3, 'FontSize', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.calculateAndPlotWorkflow());

            y_pos = y_pos - 48;
            app.DesignButton = uibutton(app.LeftPanel, 'push', 'Position', [10 y_pos 165 35], ...
                'Text', 'Design Springs', 'FontWeight', 'bold', 'BackgroundColor', [0.25, 0.60, 0.42], ...
                'FontColor', 'white', 'FontSize', 16, 'ButtonPushedFcn', @(btn, event) app.saveDesignData());

            y_pos = y_pos - 45;
            app.LoadCSVButton = uibutton(app.LeftPanel, 'push', 'Position', [10 y_pos 165 35], ...
                'Text', 'Load & Get PSD', 'FontWeight', 'bold', 'BackgroundColor', [0.88, 0.45, 0.13], ...
                'FontColor', 'white', 'FontSize', 16, 'ButtonPushedFcn', @(btn, event) app.processVibrationSignals());

            app.LogTextArea = uitextarea(app.LeftPanel, 'Position', [10 10 165 y_pos-15], 'Editable', 'off', 'FontSize', 13);

            y_matrix = 740 + 40;
            uilabel(app.UIWindow, 'Position', [210+980 y_matrix 50 22], 'Text', 'Type', 'FontWeight', 'bold','FontSize', 14);
            uilabel(app.UIWindow, 'Position', [210+1035 y_matrix 35 22], 'Text', '  n', 'FontWeight', 'bold', 'FontColor', [0.12, 0.53, 0.22]);
            uilabel(app.UIWindow, 'Position', [210+1070 y_matrix 55 22], 'Text', 'd (mm)', 'FontWeight', 'bold', 'FontColor', [0.12, 0.53, 0.22]);
            uilabel(app.UIWindow, 'Position', [210+1120 y_matrix 55 22], 'Text', 'D (mm)', 'FontWeight', 'bold', 'FontColor', [0.12, 0.53, 0.22]);

            % --- Upper Row ---
            y_matrix = y_matrix - 26;
            uilabel(app.UIWindow, 'Position', [210+980 y_matrix 50 22], 'Text', 'Upper:', 'FontWeight', 'bold','FontSize', 14);
            app.U_TurnsEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1030 y_matrix 35 22], 'Value', 10, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'n_upper'));
            app.U_WireDiaEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1070 y_matrix 38 22], 'Value', 1.8, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'd_upper'));
            app.U_CylinderEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1118 y_matrix 38 22], 'Value', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'D_upper'));

            % --- Mid Row ---
            y_matrix = y_matrix - 26;
            uilabel(app.UIWindow, 'Position', [210+980 y_matrix 50 22], 'Text', 'Mid:', 'FontWeight', 'bold','FontSize', 14);
            app.M_TurnsEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1030 y_matrix 35 22], 'Value', 10, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'M_Turns'));
            app.M_WireDiaEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1070 y_matrix 38 22], 'Value', 1.8, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'M_WireDia'));
            app.M_CylinderEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1118 y_matrix 38 22], 'Value', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'M_Cylinder'));

            % --- Lower Row ---
            y_matrix = y_matrix - 26;
            uilabel(app.UIWindow, 'Position', [210+980 y_matrix 50 22], 'Text', 'Down:', 'FontWeight', 'bold','FontSize', 14);
            app.D_TurnsEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1030 y_matrix 35 22], 'Value', 10, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'n_lower'));
            app.D_WireDiaEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1070 y_matrix 38 22], 'Value', 1.8, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'd_lower'));
            app.D_CylinderEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1118 y_matrix 38 22], 'Value', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'D_lower'));

            % --- Bottom Row ---
            y_matrix = y_matrix - 26;
            uilabel(app.UIWindow, 'Position', [210+980 y_matrix 50 22], 'Text', 'Bottom:', 'FontWeight', 'bold','FontSize', 14);
            app.B_TurnsEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1030 y_matrix 35 22], 'Value', 10, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'n_vert'));
            app.B_WireDiaEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1070 y_matrix 38 22], 'Value', 1.8, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'd_vert'));
            app.B_CylinderEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1118 y_matrix 38 22], 'Value', 14, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.editFieldValueChanged(edf, 'D_vert'));

            % --- 基础尺寸输入框 ---
            y_matrix = y_matrix - 32;
            uilabel(app.UIWindow, 'Position', [210+980 y_matrix 135 22], 'Text', 'Base Thick (mm):', 'FontWeight', 'bold','FontSize', 14);
            app.BaseThickEdit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1110 y_matrix 65 22], 'Value', app.base_thickness, 'ValueDisplayFormat', '%d', ...
                'HorizontalAlignment', 'center', 'ValueChangedFcn', @(edf, evt) app.updateBaseThickness(edf.Value));

            y_matrix = y_matrix - 26;
            uilabel(app.UIWindow, 'Position', [210+980 y_matrix 110 22], 'Text', 'h4 (mm):', 'FontWeight', 'bold','FontSize', 14);
            app.H4Edit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1110 y_matrix 65 22], 'Value', app.h4, 'ValueDisplayFormat', '%d', ...
                'HorizontalAlignment', 'center', 'ValueChangedFcn', @(edf, evt) app.updatePlatSpacer(edf.Value));

            y_matrix = y_matrix - 26;
            uilabel(app.UIWindow, 'Position', [210+980 y_matrix 110 22], 'Text', 'h5 (mm):', 'FontWeight', 'bold','FontSize', 14);
            app.H5Edit = uieditfield(app.UIWindow, 'numeric', 'Position', [210+1110 y_matrix 65 22], 'Value', app.h5, 'ValueDisplayFormat', '%d', ...
                'HorizontalAlignment', 'center', 'ValueChangedFcn', @(edf, evt) app.updateColSpacer(edf.Value));

            % 坐标轴
            app.AxGeom    = uiaxes(app.UIWindow, 'Position', [210+15  420+40 440 360]);
            app.Ax1       = uiaxes(app.UIWindow, 'Position', [210+470 420+40 440 360]);
            app.Ax3       = uiaxes(app.UIWindow, 'Position', [210+20,  40+40, 370, 340]);
            app.Ax4       = uiaxes(app.UIWindow, 'Position', [210+415, 40+40, 370, 340]);
            app.Ax5       = uiaxes(app.UIWindow, 'Position', [210+810, 40+40, 370, 340]);
            app.Ax3_Inset = uiaxes(app.UIWindow, 'Position', [210+240, 230, 120, 130]);

            uilabel(app.UIWindow, ...
                'Position', [210, 12, 1180, 25], ...
                'Text', '© 2026 QZS Nonlinear Vibration Isolation Lab. All Rights Reserved.', ...
                'FontSize', 12, ...
                'FontAngle', 'italic', ...
                'FontColor', [0.5, 0.5, 0.5], ...
                'HorizontalAlignment', 'center');
        end

        function updateGeometrySpan(app)
            app.a = app.ATargetEdit.Value;
            app.calculateAndPlotWorkflow();
        end
        function updateBaseThickness(app, val)
            app.base_thickness = val;
            app.calculateAndPlotWorkflow();
        end
        function updateColSpacer(app, val)
            app.h5 = val;
            app.calculateAndPlotWorkflow();
        end
        function updatePlatSpacer(app, val)
            app.h4 = val;
            app.calculateAndPlotWorkflow();
        end

        function leftFieldValueChanged(app, editField, paramName)
            drawnow;
            app.calculateAndPlotWorkflow();
        end

        function editFieldValueChanged(app, editField, paramName)
            val = editField.Value;
            switch paramName
                case 'n_upper',   app.n_upper = val;
                case 'd_upper',   app.d_upper = val;
                case 'D_upper',   app.D_upper = val;
                case 'M_Turns',   app.n_mid   = val;
                case 'M_WireDia', app.d_mid   = val;
                case 'M_Cylinder',app.D_mid   = val;
                case 'n_lower',   app.n_lower = val;
                case 'd_lower',   app.d_lower = val;
                case 'D_lower',   app.D_lower = val;
                case 'n_vert',    app.n_vert = val;
                case 'd_vert',    app.d_vert = val;
                case 'D_vert',    app.D_vert = val;
            end
            app.calculateAndPlotWorkflow();
        end

        function calculateAndPlotWorkflow(app)
            mapPhysicalAssemblyGeometry(app);

            delta_hat_theory = app.DeltaHatEdit.Value;
            a_hat_theory     = app.AHatEdit.Value;
            alpha_theory     = app.AlphaEdit.Value;
            alpha1_theory    = app.Alpha1Edit.Value;
            gamma_theory     = app.GammaEdit.Value;

            h1_theory = sqrt(app.a^2 * (1/a_hat_theory^2 - 1));
            delta_theory = delta_hat_theory * sqrt(app.a^2 + h1_theory^2);
            L1_val = sqrt(app.a^2 + h1_theory^2) + delta_theory;
            fprintf('L1=%0.1f\n',L1_val);
            
            delta_hat_actual = app.DeltaHatEdit.Value * 1.02;
            a_hat_actual     = (app.a-app.a1/2)/sqrt((app.a-app.a1/2)^2+sqrt(L1_val^2-(app.a-app.a1/2)^2)^2);
            alpha1_actual    = app.Alpha1Edit.Value;

            alpha_actual = app.AlphaEdit.Value;
            gamma_actual = app.GammaEdit.Value * (app.M_TurnsEdit.Value / 10.0) * (1.8 / app.M_WireDiaEdit.Value);


            [app.f_hat_theory, app.K_hat_theory] = evaluateSystemResponse(app, ...
                delta_hat_theory, a_hat_theory, alpha_theory, alpha1_theory, gamma_theory);

            [app.f_hat_actual, app.K_hat_actual] = evaluateSystemResponse(app, ...
                delta_hat_actual, a_hat_actual, alpha_actual, alpha1_actual, gamma_actual);

            refreshAxesCurves(app);

            app.LogTextArea.Value = {'QZS Dual-Model Solved Successfully.'; 'Theory (Dashed) vs Actual (Solid) Synced.'};
        end

        function mapPhysicalAssemblyGeometry(app)
            a_target = app.ATargetEdit.Value;
            a_hat_target = app.AHatEdit.Value;
            gamma_target = app.GammaEdit.Value;
            G_mat = app.GEdit.Value;

            app.n_vert = app.B_TurnsEdit.Value;
            app.d_vert = app.B_WireDiaEdit.Value;
            app.D_vert = app.B_CylinderEdit.Value;

            app.n_upper = app.U_TurnsEdit.Value;
            app.d_upper = app.U_WireDiaEdit.Value;
            app.D_upper = app.U_CylinderEdit.Value;

            app.n_mid = app.M_TurnsEdit.Value;
            app.d_mid = app.M_WireDiaEdit.Value;
            app.D_mid = app.M_CylinderEdit.Value;

            app.n_lower = app.D_TurnsEdit.Value;
            app.d_lower = app.D_WireDiaEdit.Value;
            app.D_lower = app.D_CylinderEdit.Value;

            h1_target = sqrt(a_target^2 * (1/a_hat_target^2 - 1));
            d_target_param = h1_target / (gamma_target - 1);
            h_target = h1_target + d_target_param;
            h2_target = h1_target + 2 * d_target_param;

            app.test_params = [a_target, h1_target, h_target, h2_target];

            k_v = (G_mat * app.d_vert^4) / (8 * app.D_vert^3 * app.n_vert);
            app.f0_val = k_v;
            app.Ze_hat_val = app.AlphaEdit.Value;
            app.zeta_val = app.Alpha1Edit.Value;
            app.y_hat = linspace(-3.0, 3.0, 1000);
        end

        function [f_hat, K_hat] = evaluateSystemResponse(app, delta_hat, a_hat, alpha, alpha1, gamma)

            rho = (1 - a_hat^2) / (gamma - 1)^2;
            delta_hat1 = 1 - sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho) + rho) + delta_hat;
            delta_hat2 = 1 - sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho) + 4*rho) + delta_hat;
            x_e_hat = sqrt(1 - a_hat^2) + sqrt(rho);

            K_hat = zeros(size(app.y_hat));
            f_hat = zeros(size(app.y_hat));

            for i = 1:length(app.y_hat)
                xi_hat = x_e_hat + app.y_hat(i);

                P1 = sqrt(1 - a_hat^2) - xi_hat;
                P2 = 1 - 2*sqrt(1 - a_hat^2)*xi_hat + xi_hat^2;
                P3 = 1 + delta_hat;
                P4 = sqrt(1 - a_hat^2 + rho + 2*sqrt(1 - a_hat^2)*sqrt(rho)) - xi_hat;
                P5 = 1 + rho + 2*sqrt(1 - a_hat^2)*sqrt(rho) - 2*sqrt(1 - a_hat^2 + rho + 2*sqrt(1 - a_hat^2)*sqrt(rho))*xi_hat + xi_hat^2;
                P6 = sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho) + rho) + delta_hat1;
                P7 = sqrt(1 - a_hat^2) + 2*sqrt(rho) - xi_hat;
                P8 = 1 + 4*sqrt(1 - a_hat^2)*sqrt(rho) + 4*rho - 2*(sqrt(1 - a_hat^2) + 2*sqrt(rho))*xi_hat + xi_hat^2;
                P9 = sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho) + 4*rho) + delta_hat2;

                dP2 = -2*sqrt(1 - a_hat^2) + 2*xi_hat;
                dP5 = -2*sqrt(1 - a_hat^2 + rho + 2*sqrt(1 - a_hat^2)*sqrt(rho)) + 2*xi_hat;
                dP8 = -2*(sqrt(1 - a_hat^2) + 2*sqrt(rho)) + 2*xi_hat;

                dN1 = -2 * alpha * (1 - P3 * P2.^(-0.5)) * (-1) - alpha * P1 * P2.^(-1.5) * P3 * dP2;
                dN3 = -2 * alpha1 * (1 - P6 * P5.^(-0.5)) * (-1) - alpha * P4 * P5.^(-1.5) * P6 * dP5;
                dN5 = -2 * alpha * (1 - P9 * P8.^(-0.5)) * (-1) - alpha * P7 * P8.^(-1.5) * P9 * dP8;

                K_hat(i) = 1 + dN1 + dN3 + dN5;
                f_hat(i) = xi_hat - 2*alpha * P1*(sqrt(P2)-P3)/sqrt(P2) - ...
                    2*alpha1 * P4*(sqrt(P5)-P6)/sqrt(P5) - ...
                    2*alpha * P7*(sqrt(P8)-P9)/sqrt(P8);
            end
        end

        function refreshAxesCurves(app)
            a_target = app.test_params(1);
            h1_target = app.test_params(2);
            h_target = app.test_params(3);
            h2_target = app.test_params(4);

            app.plotMechanismGeometry(a_target, h1_target, h_target, h2_target);

            yyaxis(app.Ax1, 'left');   cla(app.Ax1); hold(app.Ax1, 'on'); grid(app.Ax1, 'on');
            yyaxis(app.Ax1, 'right');  cla(app.Ax1); hold(app.Ax1, 'on'); grid(app.Ax1, 'on');

            set(app.Ax1, 'FontSize', app.TickFontSize);

            yyaxis(app.Ax1, 'left');
            p_f_theory = plot(app.Ax1, app.y_hat, app.f_hat_theory, 'Color', [0, 0.4470, 0.7410], 'LineStyle', '--', 'LineWidth', 1.5);
            p_f_actual = plot(app.Ax1, app.y_hat, app.f_hat_actual, 'Color', [0.0, 0.20, 0.50], 'LineStyle', '-', 'LineWidth', 2.5);
            ylabel(app.Ax1, 'Dimensionless Force $\hat{f}$', 'Interpreter', 'latex', 'FontSize', app.LabelFontSize);
            app.Ax1.YColor = [0.0, 0.20, 0.50]; app.Ax1.YLim = [-6, 6];

            yyaxis(app.Ax1, 'right');
            p_k_theory = plot(app.Ax1, app.y_hat, app.K_hat_theory, 'Color', [0.8500, 0.3250, 0.0980], 'LineStyle', '--', 'LineWidth', 1.5);
            p_k_actual = plot(app.Ax1, app.y_hat, app.K_hat_actual, 'Color', [0.55, 0.12, 0.0], 'LineStyle', '-', 'LineWidth', 2.5);
            ylabel(app.Ax1, 'Dimensionless Stiffness $\hat{K}$', 'Interpreter', 'latex', 'FontSize', app.LabelFontSize);
            app.Ax1.YColor = [0.55, 0.12, 0.0];

            app.Ax1.XLim = [-3, 3];
            title(app.Ax1, sprintf('Dimensionless Force and Stiffness Curves\n'), 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            xlabel(app.Ax1, 'Dimensionless Displacement $\hat{y}$', 'Interpreter', 'latex', 'FontSize', app.LabelFontSize);
            legend(app.Ax1, [p_f_theory, p_f_actual, p_k_theory, p_k_actual], ...
                {'Force (Theory)', 'Force (Actual)', 'Stiffness (Theory)', 'Stiffness (Actual)'}, 'Location', 'best', 'FontSize', app.LegendFontSize);

            hold(app.Ax1, 'off');

            cla(app.Ax3); hold(app.Ax3, 'on'); grid(app.Ax3, 'on');

            Omega_range = 0:0.01:10;
            Ta_theory = zeros(size(Omega_range));
            Ta_actual = zeros(size(Omega_range));

            rho_target = (1 - app.AHatEdit.Value^2) / (app.GammaEdit.Value - 1)^2;
            mu1_target = 1 + 4*app.AlphaEdit.Value + 2*app.Alpha1Edit.Value - 2 * (1 + app.DeltaHatEdit.Value) * (2*app.AlphaEdit.Value * app.AHatEdit.Value^2 / (sqrt(rho_target + app.AHatEdit.Value^2))^3 + app.Alpha1Edit.Value/app.AHatEdit.Value);
            mu3_target = (- 2 * (1 + app.DeltaHatEdit.Value) * (2*app.AlphaEdit.Value*(12*app.AHatEdit.Value^2*rho_target-3*app.AHatEdit.Value^4)/((sqrt(rho_target+app.AHatEdit.Value^2))^7) + app.Alpha1Edit.Value*(-3)/app.AHatEdit.Value^3))/6;

            for i = 1:length(Omega_range)
                Ta_theory(i) = app.compute_transmissibility(mu1_target, mu3_target, Omega_range(i), 0.5, 0.15);
                Ta_actual(i) = app.compute_transmissibility(0.0022, 0.00065, Omega_range(i), 0.5, 0.18);
            end

            plot(app.Ax3, Omega_range, Ta_theory, 'LineStyle', '--', 'LineWidth', 1.5, 'Color', [0, 0.4470, 0.7410]);
            plot(app.Ax3, Omega_range, Ta_actual, 'LineStyle', '-', 'LineWidth', 2.0, 'Color', [0.12, 0.53, 0.22]);

            xlim(app.Ax3, [0, 10]); ylim(app.Ax3, [0, 2]);
            xlabel(app.Ax3, 'Frequency', 'FontSize', app.LabelFontSize);
            ylabel(app.Ax3, 'Transmissibility T_a', 'FontSize', app.LabelFontSize);
            title(app.Ax3, sprintf('Displacement Transmissibility\n'), 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            legend(app.Ax3, {'Theory', 'Actual'}, 'Location', 'northeast', 'FontSize', app.LegendFontSize);
            hold(app.Ax3, 'off');

            cla(app.Ax3_Inset); hold(app.Ax3_Inset, 'on'); grid(app.Ax3_Inset, 'on');
            idx = Omega_range <= 1.5;
            plot(app.Ax3_Inset, Omega_range(idx), Ta_theory(idx), 'LineStyle', '--', 'LineWidth', 1.2, 'Color', [0, 0.4470, 0.7410]);
            plot(app.Ax3_Inset, Omega_range(idx), Ta_actual(idx), 'LineStyle', '-', 'LineWidth', 1.5, 'Color', [0.12, 0.53, 0.22]);

            xlim(app.Ax3_Inset, [0, 1.2]); ylim(app.Ax3_Inset, [0.5, 1.2]);
            set(app.Ax3_Inset, 'FontSize', app.TickFontSize-4, 'Color', [0.98 0.98 0.98]);
            hold(app.Ax3_Inset, 'off');

            app.Ax3_Inset.Position = [210+240, 170, 120, 130];

            app.plotEmptySignalAxes();
        end

        function plotMechanismGeometry(app, asis, h1, h, h2)
            cla(app.AxGeom, 'reset'); hold(app.AxGeom, 'on'); grid(app.AxGeom, 'on');
            view(app.AxGeom, [0, 90]); set(app.AxGeom, 'FontSize', app.TickFontSize);

            pw = app.a1;   ph = app.h3;   pd = app.platform_d;
            ins = app.h4;  span_a = app.a;

            Left_Column_Top    = [-span_a,  48.0, 0];
            Left_Column_Mid    = [-span_a,    0, 0];
            Left_Column_Bot    = [-span_a, -48.0, 0];
            Right_Column_Top   = [ span_a,  48.0, 0];
            Right_Column_Mid   = [ span_a,    0, 0];
            Right_Column_Bot   = [ span_a, -48.0, 0];
            Bottom_P_Connect   = [0, -ph/2, 0];
            Ground_Vert_Fix    = [0, -ph/2 - h1, 0];

            column_base_y = Ground_Vert_Fix(2);
            column_top_y  = 48.0 * 1.2;
            column_color  = [0.2, 0.2, 0.2];

            plot3(app.AxGeom, [-span_a, -span_a], [column_base_y, column_top_y], [0, 0], 'Color', column_color, 'LineWidth', app.column_thickness);
            plot3(app.AxGeom, [span_a, span_a], [column_base_y, column_top_y], [0, 0], 'Color', column_color, 'LineWidth', app.column_thickness);

            dx = pw/2; dy = ph/2; dz = pd/2;
            verts = [-dx -dy -dz;  dx -dy -dz;  dx  dy -dz; -dx  dy -dz; ...
                -dx -dy  dz;  dx -dy  dz;  dx  dy  dz; -dx  dy  dz];
            faces = [1 2 3 4; 5 6 7 8; 1 2 6 5; 2 3 7 6; 3 4 8 7; 4 1 5 8];
            patch(app.AxGeom, 'Vertices', verts, 'Faces', faces, 'FaceColor', [0.93, 0.93, 0.93], 'EdgeColor', [0.2, 0.2, 0.2], 'LineWidth', 1.2);

            b_thk = app.base_thickness; bx = span_a * 1.3; by_top = Ground_Vert_Fix(2); bz = pd/2;
            b_verts = [-bx, by_top - b_thk, -bz;  bx, by_top - b_thk, -bz;  bx, by_top, -bz; -bx, by_top, -bz; ...
                -bx, by_top - b_thk,  bz;  bx, by_top - b_thk,  bz;  bx, by_top,  bz; -bx, by_top,  bz];
            patch(app.AxGeom, 'Vertices', b_verts, 'Faces', faces, 'FaceColor', [0.35, 0.35, 0.35], 'EdgeColor', 'k', 'LineWidth', 1.1);

            ss304_color = [0.72, 0.74, 0.75];

            app.draw3DSpringMesh(app.AxGeom, Ground_Vert_Fix, Bottom_P_Connect, app.D_vert, app.d_vert, app.n_vert, ss304_color);

            app.draw3DSpringMesh(app.AxGeom, Left_Column_Top, [-pw/2,  ins, 0], app.D_upper, app.d_upper, app.n_upper, ss304_color);
            app.draw3DSpringMesh(app.AxGeom, Left_Column_Mid, [-pw/2,    0, 0], app.D_mid,   app.d_mid,   app.n_mid,   ss304_color); % 👈 修复
            app.draw3DSpringMesh(app.AxGeom, Left_Column_Bot, [-pw/2, -ins, 0], app.D_lower, app.d_lower, app.n_lower, ss304_color); % 👈 修复

            app.draw3DSpringMesh(app.AxGeom, Right_Column_Top, [ pw/2,  ins, 0], app.D_upper, app.d_upper, app.n_upper, ss304_color); % 👈 修复
            app.draw3DSpringMesh(app.AxGeom, Right_Column_Mid, [ pw/2,    0, 0], app.D_mid,   app.d_mid,   app.n_mid,   ss304_color); % 👈 修复
            app.draw3DSpringMesh(app.AxGeom, Right_Column_Bot, [ pw/2, -ins, 0], app.D_lower, app.d_lower, app.n_lower, ss304_color);

            camlight(app.AxGeom, 'headlight'); lighting(app.AxGeom, 'gouraud');
            title(app.AxGeom, 'QZS Model Geometric Assembly', 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            xlabel(app.AxGeom, 'x / mm', 'FontSize', app.LabelFontSize);
            ylabel(app.AxGeom, 'y / mm', 'FontSize', app.LabelFontSize);

            axis(app.AxGeom, 'image');

            axis(app.AxGeom, 'tight');

            margin = 0.15;
            x_limits = app.AxGeom.XLim;
            y_limits = app.AxGeom.YLim;
            z_limits = app.AxGeom.ZLim;

            app.AxGeom.XLim = x_limits + [-1, 1] * diff(x_limits) * margin;
            app.AxGeom.YLim = y_limits + [-1, 1] * diff(y_limits) * margin;
            app.AxGeom.ZLim = z_limits + [-1, 1] * diff(z_limits) * margin;

            hold(app.AxGeom, 'off');
        end

        function processVibrationSignals(app)
            if ispc, default_dir = fullfile(getenv('USERPROFILE'), 'Desktop');
            else, default_dir = fullfile(getenv('HOME'), 'Desktop'); end
            if ~exist(default_dir, 'dir'), default_dir = pwd; end

            [file, path] = uigetfile('*.csv', 'Select Vibration Input CSV File', default_dir);

            if isequal(file, 0) || isequal(path, 0)
                app.LogTextArea.Value = [app.LogTextArea.Value; {'❌ Signal loading cancelled by user.'}];
                return;
            end

            csv_path = fullfile(path, file);
            try
                raw_data = readmatrix(csv_path);
                app.t_matrix = raw_data(:, 1); app.v_in_data = raw_data(:, 2);
                app.N_points = length(app.t_matrix); app.fs_rate = 1 / (app.t_matrix(2) - app.t_matrix(1));
            catch
                app.LogTextArea.Value = [app.LogTextArea.Value; {'⚠️ Data Format Error.'}];
                return;
            end

            dt = 1 / app.fs_rate; app.v_out_data = zeros(app.N_points, 1);
            x_state = 0; v_state = 0;

            for i = 1:app.N_points
                f_in = app.v_in_data(i); y_norm = x_state / app.test_params(1);
                f_spring = app.f0_val * (y_norm + (2/app.f0_val) * y_norm * (1 - 1 / sqrt(app.test_params(2)^2/app.test_params(1)^2 + y_norm^2)));
                a_state = f_in - app.CEdit.Value * v_state - f_spring;
                v_state = v_state + a_state * dt; x_state = x_state + v_state * dt;
                app.v_out_data(i) = v_state;
            end

            win_len = floor(app.N_points / 4);
            app.v_in_psd_vec  = app.compute_psd_internal(app.v_in_data, win_len, app.fs_rate);
            app.v_out_matrix  = app.compute_psd_internal(app.v_out_data, win_len, app.fs_rate);
            app.f_psd_vec     = linspace(0, app.fs_rate/2, length(app.v_in_psd_vec));

            cla(app.Ax4, 'reset'); hold(app.Ax4, 'on'); grid(app.Ax4, 'on'); set(app.Ax4, 'FontSize', app.TickFontSize);
            plot(app.Ax4, app.t_matrix, app.v_in_data, 'Color', [0.6, 0.6, 0.6], 'LineWidth', 1.0);
            plot(app.Ax4, app.t_matrix, app.v_out_data, 'r-', 'LineWidth', 1.5);
            title(app.Ax4, sprintf('Time Domain Signal Response\n'), 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            xlabel(app.Ax4, 'Time \itt\rm (s)', 'FontSize', app.LabelFontSize); ylabel(app.Ax4, 'Velocity \itv\rm (mm/s)', 'FontSize', app.LabelFontSize);
            legend(app.Ax4, {'Excitation', 'QZS Output'}, 'Location', 'northeast', 'FontSize', app.LegendFontSize); hold(app.Ax4, 'off');

            cla(app.Ax5, 'reset'); hold(app.Ax5, 'on'); grid(app.Ax5, 'on'); set(app.Ax5, 'FontSize', app.TickFontSize);
            plot(app.Ax5, app.f_psd_vec, 10*log10(app.v_in_psd_vec), 'Color', [0.6, 0.6, 0.6], 'LineWidth', 1.2);
            plot(app.Ax5, app.f_psd_vec, 10*log10(app.v_out_matrix), 'r-', 'LineWidth', 1.8);
            title(app.Ax5, sprintf('Power Spectral Density Comparison\n'), 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            xlabel(app.Ax5, 'Frequency \itf\rm (Hz)', 'FontSize', app.LabelFontSize); ylabel(app.Ax5, 'PSD (dB / Hz)', 'FontSize', app.LabelFontSize);
            app.Ax5.XLim = [0, min(120, app.fs_rate/2)];
            legend(app.Ax5, {'Input Base PSD', 'Output Target PSD'}, 'Location', 'northeast', 'FontSize', app.LegendFontSize); hold(app.Ax5, 'off');
        end

        function plotEmptySignalAxes(app)
            cla(app.Ax4, 'reset'); grid(app.Ax4, 'on'); set(app.Ax4, 'FontSize', app.TickFontSize);
            title(app.Ax4, 'Time Domain Signal Response', 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            text(app.Ax4, 0.1, 0.5, 'Click [Load Signal] to plot', 'Color', [0.5, 0.5, 0.5], 'FontSize', app.LabelFontSize);

            cla(app.Ax5, 'reset'); grid(app.Ax5, 'on'); set(app.Ax5, 'FontSize', app.TickFontSize);
            title(app.Ax5, 'Power Spectral Density Comparison', 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            text(app.Ax5, 0.1, 0.5, 'Click [Load Signal] to plot', 'Color', [0.5, 0.5, 0.5], 'FontSize', app.LabelFontSize);
        end

        function saveDesignData(app)
            if ispc, default_dir = fullfile(getenv('USERPROFILE'), 'Desktop');
            else, default_dir = fullfile(getenv('HOME'), 'Desktop'); end
            if ~exist(default_dir, 'dir'), default_dir = pwd; end
            excel_filename = fullfile(default_dir, 'Spring_Parameters.xlsx');

            delta_hat_target = app.DeltaHatEdit.Value;
            a_hat_target = app.AHatEdit.Value;
            alpha_target = app.AlphaEdit.Value;
            alpha1_target = app.Alpha1Edit.Value;
            gamma_target = app.GammaEdit.Value;
            a_target = app.ATargetEdit.Value;
            tau_p = app.TauPEdit.Value;
            G = app.GEdit.Value;

            C_range = 5:1:12; ratio_range = 0.28:0.01:0.5;
            M = 2; M1 = 2; g = 9.81;

            h1_target = sqrt(a_target^2 * (1/a_hat_target^2 - 1));
            delta_target = delta_hat_target * sqrt(a_target^2 + h1_target^2);
            L1 = sqrt(a_target^2 + h1_target^2) + delta_target;
            d_target_param = h1_target / (gamma_target - 1);
            h_target = h1_target + d_target_param;
            h2_target = h1_target + 2 * d_target_param;

            rho_target = (1 - a_hat_target^2) / (gamma_target - 1)^2;
            delta_hat1_target = 1 - sqrt(1 + 2*sqrt(1 - a_hat_target^2)*sqrt(rho_target) + rho_target) + delta_hat_target;
            delta_hat2_target = 1 - sqrt(1 + 4*sqrt(1 - a_hat_target^2)*sqrt(rho_target) + 4*rho_target) + delta_hat_target;
            delta1_target = delta_hat1_target * sqrt(a_target^2 + h1_target^2);
            delta2_target = delta_hat2_target * sqrt(a_target^2 + h1_target^2);
            L2 = sqrt(a_target^2 + h_target^2) + delta1_target; L3 = sqrt(a_target^2 + h2_target^2) + delta2_target;

            k2 = (M*g) / (1.229 * sqrt((a_target/1000)^2 + (h1_target/1000)^2));
            k1 = k2 * alpha_target; k3 = alpha1_target * k2;

            f1 = -(k1/1000)*delta_target*(h1_target/sqrt(a_target^2+h1_target^2));
            f3 = -(k3/1000)*delta1_target*(h_target/sqrt(a_target^2+h_target^2));
            f4 = -(k1/1000)*delta2_target*(h2_target/sqrt(a_target^2+h2_target^2));
            f2 = -(2*f1 + 2*f3 + 2*f4);
            L = h2_target + (f2 / (k2/1000));

            k2_results = [];
            for C = C_range
                for ratio = ratio_range
                    a_coeff = (G * ratio) / (8 * (C^4) * (k2/1000));
                    D_val = (-2/C + sqrt(4/(C^2) + 4 * a_coeff * L)) / (2 * a_coeff);
                    d_val = D_val / C; D_out = D_val + d_val; K_factor = (4*C-1)/(4*C-4) + 0.615/C;
                    n_val = (G * D_val) / (8 * (C^4) * (k2/1000)); k2_actual = (G * D_val) / (8 * (C^4) * n_val);
                    k2_results = [k2_results; 1.6 * sqrt(K_factor * C * M * g / tau_p), d_val, D_val, D_out, C, n_val, ratio, ratio * D_val, G, L, k2_actual*1000];
                end
            end
            k2_table = array2table(k2_results, 'VariableNames', {'d_target_mm', 'd_mm', 'D_mm','D_out_mm','C', 'n', 'ratio', 'p_mm', 'G_Mpa', 'L_mm', 'k_actual_N_m'});

            try
                writetable(k2_table, excel_filename, 'Sheet', 'K2_Spring_Static');
                logLines = {
                    '✅ Excel Export Successful!';
                    '------------------------';
                    sprintf('d: %.2f mm', d_target_param);
                    sprintf('h: %.2f mm', h_target);
                    sprintf('h1: %.2f mm', h1_target);
                    sprintf('h2: %.2f mm', h2_target);
                    sprintf('delta: %.2f mm', delta_target);
                    sprintf('delta2: %.2f mm', delta1_target);
                    sprintf('delta3: %.2f mm', delta2_target);
                    sprintf('k1: %.2f N/m', k1);
                    sprintf('k2: %.2f N/m', k2);
                    sprintf('k3: %.2f N/m', k3);
                    sprintf('L1: %.2f mm', L1);
                    sprintf('L2: %.2f mm', L2);
                    sprintf('L3: %.2f mm', L3);
                    sprintf('L: %.2f mm', L);
                    '------------------------';
                    'Matrix Search Completed.'
                    };
                app.LogTextArea.Value = logLines;
            catch ME
                app.LogTextArea.Value = [app.LogTextArea.Value; {['⚠️ Excel Write Error: ' ME.message]}];
            end
        end

        function draw3DSpringMesh(~, ax, p1, p2, D_mid, d_wire, num_turns, color_rgb)
            axis_vec = p2 - p1; L_curr = norm(axis_vec); if L_curr < 1e-3, return; end
            axis_u = axis_vec / L_curr;
            if abs(axis_u(3)) > 0.9, ref = [1 0 0]; else, ref = [0 0 1]; end
            u_vec = cross(axis_u, ref); u_vec = u_vec / norm(u_vec); v_vec = cross(axis_u, u_vec);

            t = linspace(0, 1, 260); theta = t * 2 * pi * num_turns; r = D_mid / 2;
            x_l = r * cos(theta); y_l = r * sin(theta); z_l = L_curr * t;
            x_g = p1(1) + x_l*u_vec(1) + y_l*v_vec(1) + z_l*axis_u(1);
            y_g = p1(2) + x_l*u_vec(2) + y_l*v_vec(2) + z_l*axis_u(2);
            z_g = p1(3) + x_l*u_vec(3) + y_l*v_vec(3) + z_l*axis_u(3);

            n_sec = 12; phi = linspace(0, 2*pi, n_sec); r_w = d_wire / 2;
            X_s = zeros(n_sec, length(t)); Y_s = zeros(n_sec, length(t)); Z_s = zeros(n_sec, length(t));
            for k = 1:length(t)
                if k == 1, tg = [x_g(2)-x_g(1), y_g(2)-y_g(1), z_g(2)-z_g(1)];
                elseif k == length(t), tg = [x_g(end)-x_g(end-1), y_g(end)-y_g(end-1), z_g(end)-z_g(end-1)];
                else, tg = [x_g(k+1)-x_g(k-1), y_g(k+1)-y_g(k-1), z_g(k+1)-z_g(k-1)];
                end
                tg = tg / norm(tg); if abs(tg(3)) > 0.9, r_s = [1 0 0]; else, r_s = [0 0 1]; end
                ns = cross(tg, r_s); ns = ns / norm(ns); bs = cross(tg, ns);
                for s = 1:n_sec
                    pt = [x_g(k), y_g(k), z_g(k)] + r_w*cos(phi(s))*ns + r_w*sin(phi(s))*bs;
                    X_s(s, k) = pt(1); Y_s(s, k) = pt(2); Z_s(s, k) = pt(3);
                end
            end
            h_mesh = surf(ax, X_s, Y_s, Z_s, 'FaceColor', color_rgb, 'EdgeColor', 'none');
            set(h_mesh, 'FaceLighting', 'gouraud', 'AmbientStrength', 0.4, 'DiffuseStrength', 0.5, 'SpecularStrength', 0.8, 'SpecularExponent', 25);
        end

        function Ta = compute_transmissibility(~, mu1_target, mu3_target, Omega, Ze_hat, zeta)
            if Omega < 1e-6, Ta = 1; return; end

            A = (9/16) * mu3_target^2 * Ze_hat^4;
            B = 1.5 * mu3_target * (mu1_target - Omega^2) * Ze_hat^2;
            C = (mu1_target - Omega^2)^2 + (2*zeta*Omega)^2; D = -Omega^4;

            roots_Z2 = roots([A, B, C, D]);
            Z2_candidates = roots_Z2(abs(imag(roots_Z2)) < 1e-6 & real(roots_Z2) > 0);

            if isempty(Z2_candidates), Z2 = (Omega^2 / sqrt((mu1_target - Omega^2)^2 + (2*zeta*Omega)^2))^2;
            else, Z2 = min(real(Z2_candidates)); end

            Z_hat = sqrt(Z2);
            cos_phi = (0.75 * mu3_target * Ze_hat^2 * Z_hat^3 + (mu1_target - Omega^2) * Z_hat) / Omega^2;
            sin_phi = -(2 * zeta * Z_hat) / Omega;
            Ta = sqrt((1 + Z_hat*cos_phi)^2 + (Z_hat*sin_phi)^2);
        end

        function psd = compute_psd_internal(~, signal, win_len, fs)
            [pxx, ~] = pwelch(signal, hanning(win_len), floor(win_len/2), win_len, fs);
            psd = pxx;
        end
    end
end