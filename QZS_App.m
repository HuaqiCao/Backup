classdef QZS_App < matlab.apps.AppBase

    % --- 界面组件属性声明 ---
    properties (Access = public)
        UIWindow               matlab.ui.Figure
        LeftPanel              matlab.ui.container.Panel
        RightAxesPanel         matlab.ui.container.Panel 
        
        % 平铺呈现的所有坐标轴句柄
        AxGeom                 matlab.ui.control.UIAxes 
        Ax1                    matlab.ui.control.UIAxes 
        Ax3                    matlab.ui.control.UIAxes 
        Ax3_Inset              matlab.ui.control.UIAxes 
        Ax4                    matlab.ui.control.UIAxes 
        Ax5                    matlab.ui.control.UIAxes 
        
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
        
        % 3D 弹簧微调控件
        SpringTurnsEdit       matlab.ui.control.NumericEditField 
        SpringWireDiaEdit     matlab.ui.control.NumericEditField 
        SpringCylinderEdit    matlab.ui.control.NumericEditField 
        
        % 交互按钮与日志
        RunCalcButton         matlab.ui.control.Button
        LoadCSVButton         matlab.ui.control.Button
        LogTextArea           matlab.ui.control.TextArea
    end
    
    % --- 内部核心数据与可修改几何属性 ---
    properties (Access = private)
        y_hat, test_params
        f0_val, Ze_hat_val, zeta_val
        v_in_data, t_matrix, fs_rate, N_points
        v_out_matrix, f_psd_vec, v_in_psd_vec, v_out_psd_matrix
        v_out_data
        
        % 弹簧独立参数
        k_vert, L0_vert, d_vert, D_vert, n_vert
        k_upper, L0_upper, d_upper, D_upper, n_upper
        k_lower, L0_lower, d_lower, D_lower, n_lower
        
        % =================================================================
        % 【用户自定义：几何模型核心结构可控参数区】
        % 改变这里的数值，3D几何构型图中的平台结构、间距和跨度将自适应同步修改
        % =================================================================
        platform_w = 42.0;     % 1. 中间测控滑动平台的物理宽度 (X方向, mm)
        platform_h = 70.0;     % 2. 中间测控滑动平台的物理高度 (Y方向, mm)
        platform_d = 25.0;     % 3. 中间测控滑动平台的物理厚度 (Z方向, mm)
        inner_spacer_y = 18.0; % 4. 左右弹簧连接在平台侧面时的等间距垂直距离 (mm)
        outer_spacer_y = 48.0; % 5. 左右弹簧拉开连接在外部两侧立柱上的等间距垂直距离 (mm)
        spring_span_a = 60.0;  % 6. 弹簧水平安装总跨度 a (mm) (会与输入框同步)
    end

    % --- 核心生命周期与构造函数 ---
    methods (Access = public)
        function app = QZS_App()
            % 自动构建组件布局
            createComponents(app);
            
            % 注册到 App 架构中
            registerApp(app, app.UIWindow);
            
            % 首次打开应用时，默认自动计算并平铺渲染初始图像
            calculateAndExportSprings(app);
        end
        
        function delete(app)
            % 销毁窗口
            delete(app.UIWindow);
        end
    end

    % --- UI界面初始化布局与组件配置 ---
    methods (Access = private)
        function createComponents(app)
            % 主窗体
            app.UIWindow = uifigure('Name', 'QZS Nonlinear Isolation Interaction Platform (All-In-One Dashboard)', 'Position', [50 50 1420 850]);
            
            % 1. 左侧面板收窄 (宽度降为 260) - 恢复默认字体
            app.LeftPanel = uipanel(app.UIWindow, 'Title', 'Configuration', 'Position', [10 10 260 830], 'FontWeight', 'bold');
            
            y_pos = 775;
            % 使用原生 Unicode 完美渲染出带帽子的 δ̂ 符号
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'delta_hat (δ̂):', 'FontSize', 11);
            app.DeltaHatEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 0.5);
            
            y_pos = y_pos - 28;
            % 使用原生 Unicode 完美渲染出带帽子的 â 符号
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'a_hat (â):', 'FontSize', 11);
            app.AHatEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 0.755);
            
            y_pos = y_pos - 28;
            % 修复 alpha 符号渲染并恢复字体
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'alpha (α):', 'FontSize', 11);
            app.AlphaEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 0.942);
            
            y_pos = y_pos - 28;
            % 修复 alpha1 符号渲染并恢复字体
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'alpha1 (α₁):', 'FontSize', 11);
            app.Alpha1Edit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 0.501);
            
            y_pos = y_pos - 28;
            % 修复 gamma 符号渲染并恢复字体
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'gamma (γ):', 'FontSize', 11);
            app.GammaEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 2.143);
            
            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'Span a (mm):');
            app.ATargetEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 60, 'ValueChangedFcn', @(edf, evt) app.updateGeometrySpan());
            
            y_pos = y_pos - 28;
            % 修复 tau_p 符号渲染并恢复字体
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'tau_p (τ_p):', 'FontSize', 11);
            app.TauPEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 0.15);
            
            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'G (MPa):');
            app.GEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 75000);
            
            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'Damping c:');
            app.CEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 20);
            
            y_pos = y_pos - 28;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 100 22], 'Text', 'Amp Ze (mm):');
            app.ZeEdit = uieditfield(app.LeftPanel, 'numeric', 'Position', [115 y_pos 130 22], 'Value', 3);

            % 真实立体弹簧参数配置面板区 - 恢复默认字体
            y_pos = y_pos - 115;
            bg_sp = uipanel(app.LeftPanel, 'Title', '3D Spring Shape Parameters', 'Position', [5 y_pos 245 110], 'FontWeight', 'bold');
            uilabel(bg_sp, 'Position', [5 62 110 22], 'Text', 'Turns n:');
            app.SpringTurnsEdit = uieditfield(bg_sp, 'numeric', 'Position', [120 62 110 22], 'Value', 10);
            uilabel(bg_sp, 'Position', [5 34 110 22], 'Text', 'Wire dia d (mm):');
            app.SpringWireDiaEdit = uieditfield(bg_sp, 'numeric', 'Position', [120 34 110 22], 'Value', 1.8);
            uilabel(bg_sp, 'Position', [5 6 110 22], 'Text', 'Mid dia D (mm):');
            app.SpringCylinderEdit = uieditfield(bg_sp, 'numeric', 'Position', [120 6 110 22], 'Value', 14);
            
            y_pos = y_pos - 35;
            uilabel(app.LeftPanel, 'Position', [10 y_pos 90 22], 'Text', 'CSV Folder Path:');
            app.ExcelPathEdit = uieditfield(app.LeftPanel, 'text', 'Position', [100 y_pos 145 22], 'Value', pwd);
            
            y_pos = y_pos - 45;
            app.RunCalcButton = uibutton(app.LeftPanel, 'push', 'Position', [10 y_pos 235 38], 'Text', '1. Calculate & Plot All', 'FontWeight', 'bold', 'ButtonPushedFcn', @(btn, event) app.calculateAndExportSprings());
            y_pos = y_pos - 40;
            app.LoadCSVButton = uibutton(app.LeftPanel, 'push', 'Position', [10 y_pos 235 35], 'Text', '2. Load Signal & Resolve PSD', 'ButtonPushedFcn', @(btn, event) app.processVibrationSignals());
            
            app.LogTextArea = uitextarea(app.LeftPanel, 'Position', [10 10 235 y_pos-20], 'Editable', 'off');
            
            % 2. 右侧全平铺绘图大面板 - 恢复默认字体
            app.RightAxesPanel = uipanel(app.UIWindow, 'Title', 'Dashboard & Analytical Analysis View (Flat Layout)', 'Position', [280 10 1130 830], 'FontWeight', 'bold');
            
            % 上排与下排平铺坐标轴句柄组件调用
            app.AxGeom    = uiaxes(app.RightAxesPanel, 'Position', [20  420 520 360]);
            app.Ax1       = uiaxes(app.RightAxesPanel, 'Position', [570 420 520 360]);
            app.Ax3       = uiaxes(app.RightAxesPanel, 'Position', [20  40  340 340]);
            app.Ax3_Inset = uiaxes(app.RightAxesPanel, 'Position', [230 210 120 140]); 
            app.Ax4       = uiaxes(app.RightAxesPanel, 'Position', [395 40  340 340]); 
            app.Ax5       = uiaxes(app.RightAxesPanel, 'Position', [765 40  340 340]);
        end
        
        function updateGeometrySpan(app)
            app.spring_span_a = app.ATargetEdit.Value;
        end
    end

    % --- 核心计算、渲染与信号解算引擎核心逻辑 ---
    methods (Access = private)
        
        % =================================================================
        % 真实三维几何机构拓扑渲染引擎
        % =================================================================
        function plotMechanismGeometry(app, a, h1, h, h2)
            cla(app.AxGeom, 'reset');
            hold(app.AxGeom, 'on');
            grid(app.AxGeom, 'on');
            view(app.AxGeom, [0, 0, 1]); % 严格正视面投影展示
            
            set(app.AxGeom, 'FontSize', 10);
            app.spring_span_a = a; 

            % 读取解耦的可控参数
            pw = app.platform_w;   
            ph = app.platform_h;   
            pd = app.platform_d;   
            ins = app.inner_spacer_y;  
            out = app.outer_spacer_y;  
            span_a = app.spring_span_a;

            % 建立 3D 正交空间锚定骨架坐标
            Left_Column_Top    = [-span_a,  out, 0];
            Left_Column_Mid    = [-span_a,    0, 0];
            Left_Column_Bot    = [-span_a, -out, 0];
            
            Right_Column_Top   = [ span_a,  out, 0];
            Right_Column_Mid   = [ span_a,    0, 0];
            Right_Column_Bot   = [ span_a, -out, 0];
            
            Left_P_Top         = [-pw/2,  ins, 0];
            Left_P_Mid         = [-pw/2,    0, 0];
            Left_P_Bot         = [-pw/2, -ins, 0];
            
            Right_P_Top        = [ pw/2,  ins, 0];
            Right_P_Mid        = [ pw/2,    0, 0];
            Right_P_Bot        = [ pw/2, -ins, 0];
            
            Bottom_P_Connect   = [0, -ph/2, 0];             
            Ground_Vert_Fix    = [0, -ph/2 - h1, 0];        

            % 绘制外支撑连杆立柱
            plot3(app.AxGeom, [Left_Column_Top(1), Left_Column_Bot(1)], [Left_Column_Top(2)*1.2, Left_Column_Bot(2)*1.2], [0, 0], 'w-', 'LineWidth', 14);
            plot3(app.AxGeom, [Left_Column_Top(1), Left_Column_Bot(1)], [Left_Column_Top(2)*1.2, Left_Column_Bot(2)*1.2], [0, 0], 'k-', 'LineWidth', 1.0);
            plot3(app.AxGeom, [Right_Column_Top(1), Right_Column_Bot(1)], [Right_Column_Top(2)*1.2, Right_Column_Bot(2)*1.2], [0, 0], 'w-', 'LineWidth', 14);
            plot3(app.AxGeom, [Right_Column_Top(1), Right_Column_Bot(1)], [Right_Column_Top(2)*1.2, Right_Column_Bot(2)*1.2], [0, 0], 'k-', 'LineWidth', 1.0);

            % 绘制测控实体平台
            dx = pw/2; dy = ph/2; dz = pd/2;
            verts = [-dx -dy -dz;  dx -dy -dz;  dx  dy -dz; -dx  dy -dz; ...
                     -dx -dy  dz;  dx -dy  dz;  dx  dy  dz; -dx  dy  dz];
            faces = [1 2 3 4; 5 6 7 8; 1 2 6 5; 2 3 7 6; 3 4 8 7; 4 1 5 8];
            patch(app.AxGeom, 'Vertices', verts, 'Faces', faces, 'FaceColor', [0.93, 0.93, 0.93], 'EdgeColor', [0.2, 0.2, 0.2], 'LineWidth', 1.2);

            % 3D立体弹簧高级网格扫描生成
            app.draw3DSpringMesh(app.AxGeom, Ground_Vert_Fix, Bottom_P_Connect, app.D_vert, app.d_vert, app.n_vert, [0.85, 0.33, 0.10]);
            
            app.draw3DSpringMesh(app.AxGeom, Left_Column_Top, Left_P_Top, app.D_upper, app.d_upper, app.n_upper, [0.00, 0.45, 0.74]);
            app.draw3DSpringMesh(app.AxGeom, Left_Column_Mid, Left_P_Mid, app.D_upper, app.d_upper, app.n_upper, [0.00, 0.45, 0.74]);
            app.draw3DSpringMesh(app.AxGeom, Left_Column_Bot, Left_P_Bot, app.D_upper, app.d_upper, app.n_upper, [0.00, 0.45, 0.74]);
            
            app.draw3DSpringMesh(app.AxGeom, Right_Column_Top, Right_P_Top, app.D_lower, app.d_lower, app.n_lower, [0.47, 0.67, 0.19]);
            app.draw3DSpringMesh(app.AxGeom, Right_Column_Mid, Right_P_Mid, app.D_lower, app.d_lower, app.n_lower, [0.47, 0.67, 0.19]);
            app.draw3DSpringMesh(app.AxGeom, Right_Column_Bot, Right_P_Bot, app.D_lower, app.d_lower, app.n_lower, [0.47, 0.67, 0.19]);
            
            camlight(app.AxGeom, 'headlight');
            lighting(app.AxGeom, 'gouraud');
            
            title(app.AxGeom, 'QZS Physical Model Geometric Assembly (3D)', 'FontSize', 12, 'FontWeight', 'bold');
            xlabel(app.AxGeom, 'Horizontal Span X (mm)'); 
            ylabel(app.AxGeom, 'Vertical Motion Y (mm)');
            
            max_range = max([span_a, h1, out]) * 1.3;
            app.AxGeom.XLim = [-max_range*0.9, max_range*0.9]; 
            app.AxGeom.YLim = [-max_range*1.1, max_range*0.9];
            hold(app.AxGeom, 'off');
        end

        % =================================================================
        % 核心物理力学解析：无量纲刚度/力特性计算与多轴全平铺刷新
        % =================================================================
        function calculateAndExportSprings(app)
            delta_h = app.DeltaHatEdit.Value;
            a_h     = app.AHatEdit.Value;
            alpha   = app.AlphaEdit.Value;
            alpha1  = app.Alpha1Edit.Value;
            gamma   = app.GammaEdit.Value;
            a       = app.ATargetEdit.Value;
            tau_p   = app.TauPEdit.Value;
            G_mat   = app.GEdit.Value;
            
            n_turns = app.SpringTurnsEdit.Value;
            d_wire  = app.SpringWireDiaEdit.Value;
            D_tube  = app.SpringCylinderEdit.Value;
            
            app.n_vert = n_turns; app.d_vert = d_wire; app.D_vert = D_tube;
            app.n_upper = n_turns; app.d_upper = d_wire; app.D_upper = D_tube;
            app.n_lower = n_turns; app.d_lower = d_wire; app.D_lower = D_tube;

            h1 = a * sqrt(a_h^2 - (1 - delta_h)^2);
            h  = a * (1 - delta_h);
            h2 = 2 * h + h1;
            app.test_params = [a, h1, h, h2];
            
            k_v = (G_mat * d_wire^4) / (8 * D_tube^3 * n_turns);
            mu1 = 1 - (2/alpha) * (1/a_h - 1);
            mu3 = (1/alpha) * (1/a_h^3 - 1);
            app.f0_val = k_v; app.Ze_hat_val = mu1; app.zeta_val = mu3;
            
            app.y_hat = linspace(-0.6, 0.6, 300);
            f_hat = app.y_hat + (2/alpha) * app.y_hat .* (1 - 1 ./ sqrt(a_h^2 + app.y_hat.^2));
            k_hat = 1 + (2/alpha) * (1 - a_h^2 ./ (a_h^2 + app.y_hat.^2).^(1.5));

            % 刷新 3D 几何构型
            app.plotMechanismGeometry(a, h1, h, h2);

            % 刷新无量纲特性曲线 (Ax1)
            cla(app.Ax1, 'reset'); hold(app.Ax1, 'on'); grid(app.Ax1, 'on');
            set(app.Ax1, 'FontSize', 10);
            
            yyaxis(app.Ax1, 'left');
            p1 = plot(app.Ax1, app.y_hat, f_hat, 'b-', 'LineWidth', 2);
            ylabel(app.Ax1, 'Dimensionless Force \itf\rm\^', 'Interpreter', 'tex', 'Color', 'b');
            app.Ax1.YColor = 'b';
            
            yyaxis(app.Ax1, 'right');
            p2 = plot(app.Ax1, app.y_hat, k_hat, 'r--', 'LineWidth', 2);
            ylabel(app.Ax1, 'Dimensionless Stiffness \itk\rm\^', 'Interpreter', 'tex', 'Color', 'r');
            app.Ax1.YColor = 'r';
            
            title(app.Ax1, 'Dimensionless Force & Stiffness Curves', 'FontSize', 11, 'FontWeight', 'bold');
            xlabel(app.Ax1, 'Dimensionless Displacement \ity\rm\^', 'Interpreter', 'tex');
            lgd1 = legend(app.Ax1, [p1, p2], {'Force \itf\rm\^', 'Stiffness \itk\rm\^'}, 'Location', 'north');
            hold(app.Ax1, 'off');

            % 刷新位移传递率特性分析曲线 (Ax3 与内嵌 Ax3_Inset)
            cla(app.Ax3, 'reset'); hold(app.Ax3, 'on'); grid(app.Ax3, 'on');
            set(app.Ax3, 'FontSize', 9);
            cla(app.Ax3_Inset, 'reset'); hold(app.Ax3_Inset, 'on'); grid(app.Ax3_Inset, 'on');
            set(app.Ax3_Inset, 'FontSize', 7);
            
            Omega_vec = linspace(0.01, 3.5, 250);
            Ze_hat = app.ZeEdit.Value / a; 
            c_damp = app.CEdit.Value;
            zeta_damp = c_damp / (2 * sqrt(k_v * 10)); 
            
            Ta_linear = zeros(size(Omega_vec)); Ta_qzs = zeros(size(Omega_vec));
            for idx = 1:length(Omega_vec)
                Omg = Omega_vec(idx);
                Ta_linear(idx) = sqrt((1 + (2*zeta_damp*Omg)^2) / ((1 - Omg^2)^2 + (2*zeta_damp*Omg)^2));
                Ta_qzs(idx) = app.compute_transmissibility(mu1, mu3, Omg, Ze_hat, zeta_damp);
            end
            
            plot(app.Ax3, Omega_vec, 20*log10(Ta_linear), 'k--', 'LineWidth', 1.5);
            plot(app.Ax3, Omega_vec, 20*log10(Ta_qzs), 'r-', 'LineWidth', 2);
            title(app.Ax3, 'Displacement Transmissibility', 'FontSize', 11, 'FontWeight', 'bold');
            xlabel(app.Ax3, 'Frequency Ratio \Omega', 'Interpreter', 'tex');
            ylabel(app.Ax3, 'Transmissibility \itT_a\rm (dB)', 'Interpreter', 'tex');
            app.Ax3.YLim = [-40, 25];
            lgd3 = legend(app.Ax3, {'Linear System', 'QZS System'}, 'Location', 'northeast');
            set(lgd3, 'FontSize', 8);
            
            plot(app.Ax3_Inset, Omega_vec, 20*log10(Ta_linear), 'k--', 'LineWidth', 1.0);
            plot(app.Ax3_Inset, Omega_vec, 20*log10(Ta_qzs), 'r-', 'LineWidth', 1.5);
            app.Ax3_Inset.XLim = [0.1, 0.8]; app.Ax3_Inset.YLim = [-5, 12];
            title(app.Ax3_Inset, 'Low Freq Inset', 'FontSize', 7);
            hold(app.Ax3, 'off'); hold(app.Ax3_Inset, 'off');

            app.plotEmptySignalAxes();
            app.LogTextArea.Value = {'QZS Model Solved Successfully.'; 'All axes synced and tiled.'};
        end
        
        % =================================================================
        % 振动信号外部载入解算
        % =================================================================
        function processVibrationSignals(app)
            csv_dir = app.ExcelPathEdit.Value;
            csv_path = fullfile(csv_dir, 'vibration_input_data.csv');
            if ~exist(csv_path, 'file')
                app.LogTextArea.Value = [app.LogTextArea.Value; {'⚠️ CSV File Not Found!'}];
                return;
            end
            try
                raw_data = readmatrix(csv_path);
                app.t_matrix = raw_data(:, 1);
                app.v_in_data = raw_data(:, 2);
                app.N_points = length(app.t_matrix);
                app.fs_rate = 1 / (app.t_matrix(2) - app.t_matrix(1));
            catch
                app.LogTextArea.Value = [app.LogTextArea.Value; {'⚠️ Data Format Error.'}];
                return;
            end
            
            dt = 1 / app.fs_rate;
            app.v_out_data = zeros(app.N_points, 1);
            x_state = 0; v_state = 0;
            
            for i = 1:app.N_points
                f_in = app.v_in_data(i);
                y_norm = x_state / app.test_params(1);
                f_spring = app.f0_val * (y_norm + (2/app.f0_val) * y_norm * (1 - 1 / sqrt(app.test_params(2)^2/app.test_params(1)^2 + y_norm^2)));
                a_state = f_in - app.CEdit.Value * v_state - f_spring;
                v_state = v_state + a_state * dt;
                x_state = x_state + v_state * dt;
                app.v_out_data(i) = v_state; 
            end
            
            win_len = floor(app.N_points / 4);
            app.v_in_psd_vec  = app.compute_psd_internal(app.v_in_data, win_len, app.fs_rate);
            app.v_out_matrix  = app.compute_psd_internal(app.v_out_data, win_len, app.fs_rate);
            app.f_psd_vec     = linspace(0, app.fs_rate/2, length(app.v_in_psd_vec));

            % 刷新时域对比曲线 (Ax4)
            cla(app.Ax4, 'reset'); hold(app.Ax4, 'on'); grid(app.Ax4, 'on');
            set(app.Ax4, 'FontSize', 10);
            plot(app.Ax4, app.t_matrix, app.v_in_data, 'Color', [0.6, 0.6, 0.6], 'LineWidth', 1.0);
            plot(app.Ax4, app.t_matrix, app.v_out_data, 'r-', 'LineWidth', 1.5);
            title(app.Ax4, 'Time Domain Signal Response', 'FontSize', 11, 'FontWeight', 'bold');
            xlabel(app.Ax4, 'Time \itt\rm (s)', 'Interpreter', 'tex');
            ylabel(app.Ax4, 'Velocity \itv\rm (mm/s)', 'Interpreter', 'tex');
            lgd4 = legend(app.Ax4, {'Excitation', 'QZS Output'}, 'Location', 'northeast'); set(lgd4, 'FontSize', 8);
            hold(app.Ax4, 'off');

            % 刷新频域 PSD 对比分析图 (Ax5)
            cla(app.Ax5, 'reset'); hold(app.Ax5, 'on'); grid(app.Ax5, 'on');
            set(app.Ax5, 'FontSize', 10);
            plot(app.Ax5, app.f_psd_vec, 10*log10(app.v_in_psd_vec), 'Color', [0.6, 0.6, 0.6], 'LineWidth', 1.2);
            plot(app.Ax5, app.f_psd_vec, 10*log10(app.v_out_matrix), 'r-', 'LineWidth', 1.8);
            title(app.Ax5, 'Power Spectral Density (PSD) Comparison', 'FontSize', 11, 'FontWeight', 'bold');
            xlabel(app.Ax5, 'Frequency \itf\rm (Hz)', 'Interpreter', 'tex');
            ylabel(app.Ax5, 'PSD (dB / Hz)');
            app.Ax5.XLim = [0, min(120, app.fs_rate/2)];
            lgd5 = legend(app.Ax5, {'Input Base PSD', 'Output Target PSD'}, 'Location', 'northeast'); set(lgd5, 'FontSize', 8);
            hold(app.Ax5, 'off');
        end
        
        function plotEmptySignalAxes(app)
            cla(app.Ax4, 'reset'); grid(app.Ax4, 'on');
            title(app.Ax4, 'Time Domain Signal Response', 'FontSize', 11, 'FontWeight', 'bold');
            text(app.Ax4, 0.1, 0.5, 'Click [Load Signal] to plot', 'Color', [0.5, 0.5, 0.5]);
            
            cla(app.Ax5, 'reset'); grid(app.Ax5, 'on');
            title(app.Ax5, 'Power Spectral Density (PSD) Comparison', 'FontSize', 11, 'FontWeight', 'bold');
            text(app.Ax5, 0.1, 0.5, 'Click [Load Signal] to plot', 'Color', [0.5, 0.5, 0.5]);
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
            set(h_mesh, 'FaceLighting', 'gouraud', 'AmbientStrength', 0.5, 'DiffuseStrength', 0.6, 'SpecularStrength', 0.5);
        end

        function Ta = compute_transmissibility(~, mu1, mu3, Omega, Ze_h, zta)
            if Omega < 1e-6, Ta = 1; return; end
            a = (9/16) * mu3^2 * Ze_h^4; b = 1.5 * mu3 * (mu1 - Omega^2) * Ze_h^2; 
            c = (mu1 - Omega^2)^2 + (2*zta*Omega)^2; d = -Omega^4;
            roots_Z2 = roots([a, b, c, d]); Z2_candidates = roots_Z2(abs(imag(roots_Z2)) < 1e-6 & real(roots_Z2) > 0);
            if isempty(Z2_candidates), Z2 = (Omega^2 / sqrt((mu1 - Omega^2)^2 + (2*zta*Omega)^2))^2; else, Z2 = min(real(Z2_candidates)); end
            Z_hat = sqrt(Z2);
            cos_phi = (0.75 * mu3 * Ze_h^2 * Z_hat^3 + (mu1 - Omega^2) * Z_hat) / Omega^2; cos_phi = max(-1, min(1, cos_phi));
            Ta = sqrt(1 + 2 * Z_hat * cos_phi + Z_hat^2);
        end

        function psd = compute_psd_internal(~, signal, win_len, fs)
            [pxx, ~] = pwelch(signal, hanning(win_len), floor(win_len/2), win_len, fs);
            psd = pxx;
        end
    end
end