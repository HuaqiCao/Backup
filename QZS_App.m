classdef QZS_App < matlab.apps.AppBase

    % --- UI 界面组件属性声明 ---
    properties (Access = public)
        UIWindow               matlab.ui.Figure              % 主窗口句柄
        LeftPanel              matlab.ui.container.Panel     % 左侧配置控制面板
        RightAxesPanel         matlab.ui.container.Panel     % 右侧综合图表大面板

        % 平铺布局的各坐标轴句柄
        AxGeom                 matlab.ui.control.UIAxes      % 3D 机械结构拓扑图
        Ax1                    matlab.ui.control.UIAxes      % 无量纲力与刚度曲线 (双轴对比)
        Ax3                    matlab.ui.control.UIAxes      % 位移传递率分析图 (理论 vs 实际)
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
        TauPEdit              matlab.ui.control.NumericEditField  % 时间常数/剪切关联项 tau_p
        GEdit                 matlab.ui.control.NumericEditField  % 材料剪切模量 G
        CEdit                 matlab.ui.control.NumericEditField  % 系统阻尼系数 c
        ZeEdit                matlab.ui.control.NumericEditField  % 基础激振幅值 Ze

        % 3D 弹簧网格几何微调输入框 (映射为"实际"物理参数)
        SpringTurnsEdit       matlab.ui.control.NumericEditField  % 实际弹簧圈数 n
        SpringWireDiaEdit     matlab.ui.control.NumericEditField  % 实际簧丝直径 d
        SpringCylinderEdit    matlab.ui.control.NumericEditField  % 实际弹簧中径 D

        % 交互控制按钮与系统日志
        RunCalcButton         matlab.ui.control.Button            % 计算与绘图总控按钮
        LoadCSVButton         matlab.ui.control.Button            % 载入并解算外部信号按钮
        DesignButton          matlab.ui.control.Button            % 绿色保存按钮
        LogTextArea           matlab.ui.control.TextArea          % 日志信息显示文本框
    end

    % --- 全局字体与图形控制常量 ---
    properties (Access = private, Constant)
        TitleFontSize = 18;       % 图表标题字号大小
        LabelFontSize = 18;       % 坐标轴标签字号大小
        TickFontSize  = 16;       % 坐标轴刻度数字号大小
        LegendFontSize = 10;      % 图例字号大小
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
            createComponents(app);                  % 执行前端 UI 组件布局构建
            registerApp(app, app.UIWindow);         % 注册当前实例到 MATLAB App 架构
            calculateAndPlotWorkflow(app);          % 初始化加载，默认运行完整逻辑链
        end

        function delete(app)
            delete(app.UIWindow);                   % 显式安全销毁主窗体
        end
    end

    methods (Access = private)

        % --- 前端 UI 界面组件布局构建 ---
        function createComponents(app)
            % 主窗体初始化
            app.UIWindow = uifigure('Name', 'QZS Nonlinear Isolation System Pro', 'Position', [50 50 1420 850]);

            % 1. 左侧配置控制面板构建
            app.LeftPanel = uipanel(app.UIWindow, 'Title', 'Configuration', 'Position', [10 10 190 830], 'FontWeight', 'bold');

            y_pos = 775;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'delta_hat (δ̂):', 'FontSize', 12, 'FontWeight', 'bold');
            app.DeltaHatEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', 0.5, 'HorizontalAlignment', 'center');

            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'a_hat (â):', 'FontSize', 12, 'FontWeight', 'bold');
            app.AHatEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', 0.755, 'HorizontalAlignment', 'center');

            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'alpha (α):', 'FontSize', 12, 'FontWeight', 'bold');
            app.AlphaEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', 0.942, 'HorizontalAlignment', 'center');

            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'alpha1 (α₁):', 'FontSize', 12, 'FontWeight', 'bold');
            app.Alpha1Edit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', 0.501, 'HorizontalAlignment', 'center');

            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'gamma (γ):', 'FontSize', 12, 'FontWeight', 'bold');
            app.GammaEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', 2.143, 'HorizontalAlignment', 'center');

            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'a (mm):', 'FontSize', 12, 'FontWeight', 'bold');
            app.ATargetEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', app.a, 'HorizontalAlignment', 'center', ...
                'ValueChangedFcn', @(edf, evt) app.updateGeometrySpan());

            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'tau_p (Mpa):', 'FontSize', 12, 'FontWeight', 'bold');
            app.TauPEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', 70.0, 'HorizontalAlignment', 'center');

            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'G (MPa):', 'FontSize', 12, 'FontWeight', 'bold');
            app.GEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', 75000, 'HorizontalAlignment', 'center');

            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'Damping C:', 'FontSize', 12, 'FontWeight', 'bold');
            app.CEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', 20, 'HorizontalAlignment', 'center');

            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 80 22], 'Text', 'Ze (mm):', 'FontSize', 12, 'FontWeight', 'bold');
            app.ZeEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [90 y_pos 85 22], 'Value', 3, 'HorizontalAlignment', 'center');

            % 交互控制按钮区
            y_pos = y_pos - 45;
            app.DesignButton = uibutton(app.LeftPanel, 'push', 'Position', [10 y_pos 165 35], ...
                'Text', 'Design Springs', 'FontWeight', 'bold', 'BackgroundColor', [0.25, 0.60, 0.42], ...
                'FontColor', 'white', 'FontSize', 16, 'ButtonPushedFcn', @(btn, event) app.saveDesignData());

            y_pos = y_pos - 42;
            app.RunCalcButton = uibutton(app.LeftPanel, 'push', 'Position', [10 y_pos 165 38], ...
                'Text', 'Calculate & Plot', 'FontWeight', 'bold', 'BackgroundColor', [0.18, 0.49, 0.71], ...
                'FontColor', 'white', 'FontSize', 16, 'ButtonPushedFcn', @(btn, event) app.calculateAndPlotWorkflow());

            y_pos = y_pos - 45;
            app.LoadCSVButton = uibutton(app.LeftPanel, 'push', 'Position', [10 y_pos 165 35], ...
                'Text', 'Load & Get PSD', 'FontWeight', 'bold', 'BackgroundColor', [0.88, 0.45, 0.13], ...
                'FontColor', 'white', 'FontSize', 16, 'ButtonPushedFcn', @(btn, event) app.processVibrationSignals());

            app.LogTextArea = uitextarea(app.LeftPanel, 'Position', [10 10 165 y_pos-15], 'Editable', 'off');

            % 2. 右侧大绘图展示面板及高级自适应实际参数控制器
            app.RightAxesPanel = uipanel(app.UIWindow, 'Title', 'Dashboard & Analytical Analysis View (Flat Layout)', 'Position', [210 10 1125 830], 'FontWeight', 'bold');

            y_geom_ctrl = 740;
            uilabel(app.RightAxesPanel, 'Position', [940 y_geom_ctrl 110 22], 'Text', 'Base Thick (mm):', 'FontWeight', 'bold');
            uieditfield(app.RightAxesPanel, 'numeric', 'Position', [1050 y_geom_ctrl 65 22], 'Value', app.base_thickness, 'ValueDisplayFormat', '%d', ...
                'HorizontalAlignment', 'center', 'ValueChangedFcn', @(edf, evt) app.updateBaseThickness(edf.Value));

            y_geom_ctrl = y_geom_ctrl - 28;
            uilabel(app.RightAxesPanel, 'Position', [940 y_geom_ctrl 110 22], 'Text', 'h4 (mm):', 'FontWeight', 'bold');
            uieditfield(app.RightAxesPanel, 'numeric', 'Position', [1050 y_geom_ctrl 65 22], 'Value', app.h4, 'ValueDisplayFormat', '%d', ...
                'HorizontalAlignment', 'center', 'ValueChangedFcn', @(edf, evt) app.updatePlatSpacer(edf.Value));

            y_geom_ctrl = y_geom_ctrl - 28;
            uilabel(app.RightAxesPanel, 'Position', [940 y_geom_ctrl 110 22], 'Text', 'h5 (mm):', 'FontWeight', 'bold');
            uieditfield(app.RightAxesPanel, 'numeric', 'Position', [1050 y_geom_ctrl 65 22], 'Value', app.h5, 'ValueDisplayFormat', '%d', ...
                'HorizontalAlignment', 'center', 'ValueChangedFcn', @(edf, evt) app.updateColSpacer(edf.Value));

            % 实际加工微调尺寸控制区
            y_geom_ctrl = y_geom_ctrl - 32;
            uilabel(app.RightAxesPanel, 'Position', [940 y_geom_ctrl 110 22], 'Text', 'Actual n:', 'FontWeight', 'bold', 'FontColor', [0.12, 0.53, 0.22]);
            app.SpringTurnsEdit = uieditfield(app.RightAxesPanel, 'numeric', 'Position', [1050 y_geom_ctrl 65 22], 'Value', 10, ...
                'HorizontalAlignment', 'center', 'ValueChangedFcn', @(edf, evt) app.calculateAndPlotWorkflow());

            y_geom_ctrl = y_geom_ctrl - 28;
            uilabel(app.RightAxesPanel, 'Position', [940 y_geom_ctrl 110 22], 'Text', 'Actual d (mm):', 'FontWeight', 'bold', 'FontColor', [0.12, 0.53, 0.22]);
            app.SpringWireDiaEdit = uieditfield(app.RightAxesPanel, 'numeric', 'Position', [1050 y_geom_ctrl 65 22], 'Value', 1.8, ...
                'HorizontalAlignment', 'center', 'ValueChangedFcn', @(edf, evt) app.calculateAndPlotWorkflow());

            y_geom_ctrl = y_geom_ctrl - 28;
            uilabel(app.RightAxesPanel, 'Position', [940 y_geom_ctrl 110 22], 'Text', 'Actual D (mm):', 'FontWeight', 'bold', 'FontColor', [0.12, 0.53, 0.22]);
            app.SpringCylinderEdit = uieditfield(app.RightAxesPanel, 'numeric', 'Position', [1050 y_geom_ctrl 65 22], 'Value', 14, ...
                'HorizontalAlignment', 'center', 'ValueChangedFcn', @(edf, evt) app.calculateAndPlotWorkflow());

            % 初始化平铺的各图形显示坐标轴位置
            app.AxGeom    = uiaxes(app.RightAxesPanel, 'Position', [15  420 450 360]);
            app.Ax1       = uiaxes(app.RightAxesPanel, 'Position', [480 420 450 360]);
            app.Ax3       = uiaxes(app.RightAxesPanel, 'Position', [15  40  340 340]);
            app.Ax3_Inset = uiaxes(app.RightAxesPanel, 'Position', [215 210 120 140]);
            app.Ax4       = uiaxes(app.RightAxesPanel, 'Position', [375 40  340 340]);
            app.Ax5       = uiaxes(app.RightAxesPanel, 'Position', [735 40  340 340]);
        end

        % --- 几何尺寸联动更新回调函数群 ---
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

        % --- 核心工作流总递推控制中心 ---
        function calculateAndPlotWorkflow(app)
            % 1. 物理结构基本几何学前置推导
            mapPhysicalAssemblyGeometry(app);
            
            % 2. 代数离散求解：理论设计无量纲指标
            [app.f_hat_theory, app.K_hat_theory] = evaluateSystemResponse(app, ...
                app.DeltaHatEdit.Value, app.AHatEdit.Value, app.AlphaEdit.Value, app.Alpha1Edit.Value, app.GammaEdit.Value);
            
            % 3. 代数离散求解：计入加工误差/实际位置微调后的非线性指标表现
            % 此处模拟实际微调：引入实际簧丝和圈数产生的几何偏置扰动修正系数
            actual_gamma_bias = app.GammaEdit.Value * (app.SpringTurnsEdit.Value / 10.0) * (1.8 / app.SpringWireDiaEdit.Value);
            actual_alpha_bias = app.AlphaEdit.Value * (app.SpringCylinderEdit.Value / 14.0)^3;
            [app.f_hat_actual, app.K_hat_actual] = evaluateSystemResponse(app, ...
                app.DeltaHatEdit.Value * 1.02, app.AHatEdit.Value * 0.99, actual_alpha_bias, app.Alpha1Edit.Value * 0.95, actual_gamma_bias);

            % 4. 刷新底层渲染图层资产
            refreshAxesCurves(app);
            
            app.LogTextArea.Value = {'QZS Dual-Model Solved Successfully.'; 'Theory (Dashed) vs Actual (Solid) Synced.'};
        end

        % --- 模块化函数：几何空间构型转换 ---
        function mapPhysicalAssemblyGeometry(app)
            a_target = app.ATargetEdit.Value;
            a_hat_target = app.AHatEdit.Value;
            gamma_target = app.GammaEdit.Value;
            G_mat = app.GEdit.Value;
            
            n_turns = app.SpringTurnsEdit.Value;
            d_wire = app.SpringWireDiaEdit.Value;
            D_tube = app.SpringCylinderEdit.Value;

            app.n_vert = n_turns; app.d_vert = d_wire; app.D_vert = D_tube;
            app.n_upper = n_turns; app.d_upper = d_wire; app.D_upper = D_tube;
            app.n_lower = n_turns; app.d_lower = d_wire; app.D_lower = D_tube;

            h1_target = sqrt(a_target^2 * (1/a_hat_target^2 - 1));
            d_target_param = h1_target / (gamma_target - 1);
            h_target = h1_target + d_target_param;
            h2_target = h1_target + 2 * d_target_param;
            
            app.test_params = [a_target, h1_target, h_target, h2_target];
            k_v = (G_mat * d_wire^4) / (8 * D_tube^3 * n_turns);
            app.f0_val = k_v; 
            app.Ze_hat_val = app.AlphaEdit.Value; 
            app.zeta_val = app.Alpha1Edit.Value;
            app.y_hat = linspace(-3.0, 3.0, 1000);
        end

        % --- 模块化函数：通用的高阶非线性恢复力与刚度离散数值核心求解器 ---
        function [f_curve, K_curve] = evaluateSystemResponse(app, delta_h, a_h, alpha_v, alpha1_v, gamma_v)
            rho_val = (1 - a_h^2) / (gamma_v - 1)^2;
            delta_hat1_val = 1 - sqrt(1 + 2*sqrt(1 - a_h^2)*sqrt(rho_val) + rho_val) + delta_h;
            delta_hat2_val = 1 - sqrt(1 + 4*sqrt(1 - a_h^2)*sqrt(rho_val) + 4*rho_val) + delta_h;
            x_e_hat_val = sqrt(1 - a_h^2) + sqrt(rho_val);

            K_curve = zeros(size(app.y_hat));
            f_curve = zeros(size(app.y_hat));

            for i = 1:length(app.y_hat)
                xi_h = x_e_hat_val + app.y_hat(i);
                P1 = sqrt(1 - a_h^2) - xi_h;
                P2 = 1 - 2*sqrt(1 - a_h^2)*xi_h + xi_h^2;
                P3 = 1 + delta_h;
                P4 = sqrt(1 - a_h^2 + rho_val + 2*sqrt(1 - a_h^2)*sqrt(rho_val)) - xi_h;
                P5 = 1 + rho_val + 2*sqrt(1 - a_h^2)*sqrt(rho_val) - 2*sqrt(1 - a_h^2 + rho_val + 2*sqrt(1 - a_h^2)*sqrt(rho_val))*xi_h + xi_h^2;
                P6 = sqrt(1 + 2*sqrt(1 - a_h^2)*sqrt(rho_val) + rho_val) + delta_hat1_val;
                P7 = sqrt(1 - a_h^2) + 2*sqrt(rho_val) - xi_h;
                P8 = 1 + 4*sqrt(1 - a_h^2)*sqrt(rho_val) + 4*rho_val - 2*(sqrt(1 - a_h^2) + 2*sqrt(rho_val))*xi_h + xi_h^2;
                P9 = sqrt(1 + 4*sqrt(1 - a_h^2)*sqrt(rho_val) + 4*rho_val) + delta_hat2_val;

                dP2 = -2*sqrt(1 - a_h^2) + 2*xi_h;
                dP5 = -2*sqrt(1 - a_h^2 + rho_val + 2*sqrt(1 - a_h^2)*sqrt(rho_val)) + 2*xi_h;
                dP8 = -2*(sqrt(1 - a_h^2) + 2*sqrt(rho_val)) + 2*xi_h;

                dN1 = -2 * alpha_v * (1 - P3 * P2.^(-0.5)) * (-1) - alpha_v * P1 * P2.^(-1.5) * P3 * dP2;
                dN3 = -2 * alpha1_v * (1 - P6 * P5.^(-0.5)) * (-1) - alpha_v * P4 * P5.^(-1.5) * P6 * dP5;
                dN5 = -2 * alpha_v * (1 - P9 * P8.^(-0.5)) * (-1) - alpha_v * P7 * P8.^(-1.5) * P9 * dP8;

                K_curve(i) = 1 + dN1 + dN3 + dN5;
                f_curve(i) = xi_h - 2*alpha_v * P1*(sqrt(P2)-P3)/sqrt(P2) - ...
                    2*alpha1_v * P4*(sqrt(P5)-P6)/sqrt(P5) - ...
                    2*alpha_v * P7*(sqrt(P8)-P9)/sqrt(P8);
            end
        end

        % --- 模块化函数：综合多轴联动图表重绘更新中心 ---
        function refreshAxesCurves(app)
            % 解构公用空间尺度
            a_target = app.test_params(1);   h1_target = app.test_params(2);
            h_target = app.test_params(3);   h2_target = app.test_params(4);

            % 1. 刷新 3D 拓扑结构装配图
            app.plotMechanismGeometry(a_target, h1_target, h_target, h2_target);

            % 2. 刷新并双轴联动对比图表 (Ax1)
            cla(app.Ax1, 'reset'); hold(app.Ax1, 'on'); grid(app.Ax1, 'on');
            set(app.Ax1, 'FontSize', app.TickFontSize);

            % --- 左侧双轴：无量纲力对比 ---
            yyaxis(app.Ax1, 'left');
            p_f_theory = plot(app.Ax1, app.y_hat, app.f_hat_theory, 'Color', [0, 0.4470, 0.7410], 'LineStyle', '--', 'LineWidth', 1.5);
            p_f_actual = plot(app.Ax1, app.y_hat, app.f_hat_actual, 'Color', [0.12, 0.53, 0.22], 'LineStyle', '-', 'LineWidth', 2.0); % 实际表现线
            ylabel(app.Ax1, 'Dimensionless Force $\hat{f}$', 'Interpreter', 'latex', 'FontSize', app.LabelFontSize);
            app.Ax1.YColor = [0, 0.4470, 0.7410]; app.Ax1.YLim = [-6, 6];

            % --- 右侧双轴：无量纲刚度对比 ---
            yyaxis(app.Ax1, 'right');
            p_k_theory = plot(app.Ax1, app.y_hat, app.K_hat_theory, 'Color', [0.8500, 0.3250, 0.0980], 'LineStyle', '--', 'LineWidth', 1.5);
            p_k_actual = plot(app.Ax1, app.y_hat, app.K_hat_actual, 'Color', [0.49, 0.18, 0.56], 'LineStyle', '-', 'LineWidth', 2.0); % 实际表现线
            ylabel(app.Ax1, 'Dimensionless Stiffness $\hat{K}$', 'Interpreter', 'latex', 'FontSize', app.LabelFontSize);
            app.Ax1.YColor = [0.8500, 0.3250, 0.0980];

            app.Ax1.XLim = [-3, 3];
            title(app.Ax1, sprintf('Dimensionless Force and Stiffness Curves\n'), 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            xlabel(app.Ax1, 'Dimensionless Displacement $\hat{y}$', 'Interpreter', 'latex', 'FontSize', app.LabelFontSize);
            legend(app.Ax1, [p_f_theory, p_f_actual, p_k_theory, p_k_actual], ...
                {'Force (Theory)', 'Force (Actual)', 'Stiffness (Theory)', 'Stiffness (Actual)'}, 'Location', 'best', 'FontSize', app.LegendFontSize);
            hold(app.Ax1, 'off');

            % 3. 刷新位移传递率曲线对比分析图 (Ax3)
            cla(app.Ax3); hold(app.Ax3, 'on'); grid(app.Ax3, 'on');
            
            Omega_range = 0:0.01:10;
            Ta_theory = zeros(size(Omega_range));
            Ta_actual = zeros(size(Omega_range));

            for i = 1:length(Omega_range)
                Ta_theory(i) = app.compute_transmissibility(0.0017, 0.00048, Omega_range(i), 0.5, 0.15);
                % 实际模型对应的高频扰动与略高的阻尼表现传递系数
                Ta_actual(i) = app.compute_transmissibility(0.0022, 0.00065, Omega_range(i), 0.5, 0.18);
            end

            plot(app.Ax3, Omega_range, Ta_theory, 'LineStyle', '--', 'LineWidth', 1.5, 'Color', 'r');
            plot(app.Ax3, Omega_range, Ta_actual, 'LineStyle', '-', 'LineWidth', 2.0, 'Color', [0.12, 0.53, 0.22]); % 绿色代表实际加工传递率
            
            xlim(app.Ax3, [0, 10]); ylim(app.Ax3, [0, 2]);
            xlabel(app.Ax3, 'Frequency', 'FontSize', app.LabelFontSize);
            ylabel(app.Ax3, 'Transmissibility T_a', 'FontSize', app.LabelFontSize);
            title(app.Ax3, sprintf('Displacement Transmissibility\n'), 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            legend(app.Ax3, {'Theory', 'Actual'},'Location', 'northeast', 'FontSize', app.LegendFontSize);
            hold(app.Ax3, 'off');

            cla(app.Ax3_Inset); hold(app.Ax3_Inset, 'on'); grid(app.Ax3_Inset, 'on');
            % 截取低频共振核心段 [0, 3]
            idx = Omega_range <= 1.5;
            plot(app.Ax3_Inset, Omega_range(idx), Ta_theory(idx), 'LineStyle', '--', 'LineWidth', 1.2, 'Color', 'r');
            plot(app.Ax3_Inset, Omega_range(idx), Ta_actual(idx), 'LineStyle', '-', 'LineWidth', 1.5, 'Color', [0.12, 0.53, 0.22]);
            
            % 设定紧凑的小图坐标范围和微型刻度
            xlim(app.Ax3_Inset, [0, 1.2]); ylim(app.Ax3_Inset, [0.5, 1.2]);
            set(app.Ax3_Inset, 'FontSize', app.TickFontSize-4, 'Color', [0.98 0.98 0.98]); 
            hold(app.Ax3_Inset, 'off');
            app.Ax3_Inset.Position = [225, 140, 110, 120];

            % 初始化或清空实测信号外部数据缓存时域面板
            app.plotEmptySignalAxes();
        end

        % --- 建立准零刚度物理隔振系统的 3D 空间几何拓扑并渲染 ---
        function plotMechanismGeometry(app, a, h1, h, h2)
            cla(app.AxGeom, 'reset'); hold(app.AxGeom, 'on'); grid(app.AxGeom, 'on');
            view(app.AxGeom, [1, 1, 1]); set(app.AxGeom, 'FontSize', app.TickFontSize);

            app.a = a;
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

            % 绘制支架立柱
            plot3(app.AxGeom, [-span_a, -span_a], [column_base_y, column_top_y], [0, 0], 'Color', column_color, 'LineWidth', app.column_thickness);
            plot3(app.AxGeom, [span_a, span_a], [column_base_y, column_top_y], [0, 0], 'Color', column_color, 'LineWidth', app.column_thickness);

            % 绘制中间滑动载荷平台
            dx = pw/2; dy = ph/2; dz = pd/2;
            verts = [-dx -dy -dz;  dx -dy -dz;  dx  dy -dz; -dx  dy -dz; ...
                -dx -dy  dz;  dx -dy  dz;  dx  dy  dz; -dx  dy  dz];
            faces = [1 2 3 4; 5 6 7 8; 1 2 6 5; 2 3 7 6; 3 4 8 7; 4 1 5 8];
            patch(app.AxGeom, 'Vertices', verts, 'Faces', faces, 'FaceColor', [0.93, 0.93, 0.93], 'EdgeColor', [0.2, 0.2, 0.2], 'LineWidth', 1.2);

            % 轴孔销钉渲染
            hole_r = 3.2;  hole_len = 3.0;
            [hc_z, hc_x, hc_y] = cylinder(hole_r, 24); hc_z = hc_z * hole_len;
            hole_heights = [app.h4, 0, -app.h4];
            for hh = hole_heights
                surf(app.AxGeom, -hc_z - dx + 0.1, hc_x, hc_y + hh, 'FaceColor', [0.15, 0.15, 0.15], 'EdgeColor', [0.3, 0.3, 0.3]);
                surf(app.AxGeom, hc_z + dx - 0.1, hc_x, hc_y + hh, 'FaceColor', [0.15, 0.15, 0.15], 'EdgeColor', [0.3, 0.3, 0.3]);
            end

            % 地基渲染
            b_thk = app.base_thickness; bx = span_a * 1.3; by_top = Ground_Vert_Fix(2); bz = pd/2;
            b_verts = [-bx, by_top - b_thk, -bz;  bx, by_top - b_thk, -bz;  bx, by_top, -bz; -bx, by_top, -bz; ...
                -bx, by_top - b_thk,  bz;  bx, by_top - b_thk,  bz;  bx, by_top,  bz; -bx, by_top,  bz];
            patch(app.AxGeom, 'Vertices', b_verts, 'Faces', faces, 'FaceColor', [0.35, 0.35, 0.35], 'EdgeColor', 'k', 'LineWidth', 1.1);

            % 不锈钢弹簧丝曲面拓扑映射网格绘制
            ss304_color = [0.72, 0.74, 0.75];
            app.draw3DSpringMesh(app.AxGeom, Ground_Vert_Fix, Bottom_P_Connect, app.D_vert, app.d_vert, app.n_vert, ss304_color);
            app.draw3DSpringMesh(app.AxGeom, Left_Column_Top, [-pw/2,  ins, 0], app.D_upper, app.d_upper, app.n_upper, ss304_color);
            app.draw3DSpringMesh(app.AxGeom, Left_Column_Mid, [-pw/2,    0, 0], app.D_upper, app.d_upper, app.n_upper, ss304_color);
            app.draw3DSpringMesh(app.AxGeom, Left_Column_Bot, [-pw/2, -ins, 0], app.D_upper, app.d_upper, app.n_upper, ss304_color);
            app.draw3DSpringMesh(app.AxGeom, Right_Column_Top, [ pw/2,  ins, 0], app.D_lower, app.d_lower, app.n_lower, ss304_color);
            app.draw3DSpringMesh(app.AxGeom, Right_Column_Mid, [ pw/2,    0, 0], app.D_lower, app.d_lower, app.n_lower, ss304_color);
            app.draw3DSpringMesh(app.AxGeom, Right_Column_Bot, [ pw/2, -ins, 0], app.D_lower, app.d_lower, app.n_lower, ss304_color);

            camlight(app.AxGeom, 'headlight'); lighting(app.AxGeom, 'gouraud');
            title(app.AxGeom, 'QZS Model Geometric Assembly', 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            xlabel(app.AxGeom, 'x / mm', 'FontSize', app.LabelFontSize);
            ylabel(app.AxGeom, 'y / mm', 'FontSize', app.LabelFontSize);

            max_range = max([span_a, h1, 48.0]) * 1.3;
            app.AxGeom.XLim = [-max_range*0.9, max_range*0.9]; app.AxGeom.YLim = [-max_range*1.1, max_range*0.9];
            hold(app.AxGeom, 'off');
        end

        % --- 读取外部实测振动信号并执行动力学数值解算 ---
        function processVibrationSignals(app)
            if ispc, default_dir = fullfile(getenv('USERPROFILE'), 'Desktop');
            else, default_dir = fullfile(getenv('HOME'), 'Desktop'); end
            if ~exist(default_dir, 'dir'), default_dir = pwd; end

            csv_path = fullfile(default_dir, 'vibration_input_data.csv');
            if ~exist(csv_path, 'file')
                app.LogTextArea.Value = [app.LogTextArea.Value; {'⚠️ vibration_input_data.csv not found on Desktop!'}];
                return;
            end
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

            % 刷新时域动态对比曲线 (Ax4)
            cla(app.Ax4, 'reset'); hold(app.Ax4, 'on'); grid(app.Ax4, 'on'); set(app.Ax4, 'FontSize', app.TickFontSize);
            plot(app.Ax4, app.t_matrix, app.v_in_data, 'Color', [0.6, 0.6, 0.6], 'LineWidth', 1.0);
            plot(app.Ax4, app.t_matrix, app.v_out_data, 'r-', 'LineWidth', 1.5);
            title(app.Ax4, sprintf('Time Domain Signal Response\n'), 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            xlabel(app.Ax4, 'Time \itt\rm (s)', 'FontSize', app.LabelFontSize); ylabel(app.Ax4, 'Velocity \itv\rm (mm/s)', 'FontSize', app.LabelFontSize);
            legend(app.Ax4, {'Excitation', 'QZS Output'}, 'Location', 'northeast', 'FontSize', app.LegendFontSize); hold(app.Ax4, 'off');

            % 刷新频域功率谱密度衰减对比分析图 (Ax5)
            cla(app.Ax5, 'reset'); hold(app.Ax5, 'on'); grid(app.Ax5, 'on'); set(app.Ax5, 'FontSize', app.TickFontSize);
            plot(app.Ax5, app.f_psd_vec, 10*log10(app.v_in_psd_vec), 'Color', [0.6, 0.6, 0.6], 'LineWidth', 1.2);
            plot(app.Ax5, app.f_psd_vec, 10*log10(app.v_out_matrix), 'r-', 'LineWidth', 1.8);
           title(app.Ax5, sprintf('Power Spectral Density Comparison\n'), 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            xlabel(app.Ax5, 'Frequency \itf\rm (Hz)', 'FontSize', app.LabelFontSize); ylabel(app.Ax5, 'PSD (dB / Hz)', 'FontSize', app.LabelFontSize);
            app.Ax5.XLim = [0, min(120, app.fs_rate/2)];
            legend(app.Ax5, {'Input Base PSD', 'Output Target PSD'}, 'Location', 'northeast', 'FontSize', app.LegendFontSize); hold(app.Ax5, 'off');
        end

        % --- 状态复位占位提示区 ---
        function plotEmptySignalAxes(app)
            cla(app.Ax4, 'reset'); grid(app.Ax4, 'on'); set(app.Ax4, 'FontSize', app.TickFontSize);
            title(app.Ax4, 'Time Domain Signal Response', 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            text(app.Ax4, 0.1, 0.5, 'Click [Load Signal] to plot', 'Color', [0.5, 0.5, 0.5], 'FontSize', app.LabelFontSize);

            cla(app.Ax5, 'reset'); grid(app.Ax5, 'on'); set(app.Ax5, 'FontSize', app.TickFontSize);
            title(app.Ax5, 'Power Spectral Density (PSD) Comparison', 'FontSize', app.TitleFontSize, 'FontWeight', 'bold');
            text(app.Ax5, 0.1, 0.5, 'Click [Load Signal] to plot', 'Color', [0.5, 0.5, 0.5], 'FontSize', app.LabelFontSize);
        end

        % --- 多约束嵌套迭代计算并多 Sheet 导出参数 ---
        function saveDesignData(app)
            if ispc, default_dir = fullfile(getenv('USERPROFILE'), 'Desktop');
            else, default_dir = fullfile(getenv('HOME'), 'Desktop'); end
            if ~exist(default_dir, 'dir'), default_dir = pwd; end

            [filename, pathname] = uiputfile({'*.xlsx', 'Excel Files (*.xlsx)'}, ...
                'Export Spring Design Parameters to Excel', fullfile(default_dir, 'Spring_Parameters.xlsx'));

            if isequal(filename,0) || isequal(pathname,0)
                app.LogTextArea.Value = [app.LogTextArea.Value; {'❌ Export cancelled by user.'}]; return;
            end
            excel_filename = fullfile(pathname, filename);

            % 同步参数做工程矩阵搜索
            delta_hat_target = app.DeltaHatEdit.Value; a_hat_target = app.AHatEdit.Value;
            alpha_target = app.AlphaEdit.Value; alpha1_target = app.Alpha1Edit.Value;
            gamma_target = app.GammaEdit.Value; a_target = app.ATargetEdit.Value;
            tau_p = app.TauPEdit.Value; G = app.GEdit.Value;

            C_range = 5:1:12; ratio_range = 0.28:0.01:0.5; M = 2; M1 = 2; g = 9.81;

            h1_target = sqrt(a_target^2 * (1/a_hat_target^2 - 1));
            delta_target = delta_hat_target * sqrt(a_target^2 + h1_target^2);
            L1 = sqrt(a_target^2 + h1_target^2) + delta_target;
            d_target_param = h1_target / (gamma_target - 1);
            h_target = h1_target + d_target_param; h2_target = h1_target + 2 * d_target_param;

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
            f2 = -(2*f1 + 2*f3 + 2*f4); L = h2_target + (f2 / (k2/1000));

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
                app.LogTextArea.Value = [app.LogTextArea.Value; {'Excel Export Successful!'}];
            catch ME
                app.LogTextArea.Value = [app.LogTextArea.Value; {['⚠️ Excel Write Error: ' ME.message]}];
            end
        end

        % --- 利用 Frenet-Serret 标架构建 3D 螺旋线弹簧管网格曲面 ---
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

        % --- 高阶非线性动力学幅频控制代数方程多项式求根判定 ---
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

        % --- 内置时域信号 Welch 功率谱密度提取法封装 ---
        function psd = compute_psd_internal(~, signal, win_len, fs)
            [pxx, ~] = pwelch(signal, hanning(win_len), floor(win_len/2), win_len, fs);
            psd = pxx;
        end

    end % 对应 private methods 闭合
end % 对应 classdef 全类闭合