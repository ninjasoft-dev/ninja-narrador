"""Interface desktop do NinjaSoft Narrator."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from .config import NarratorConfig, load_config
from .domain import NarrationRequest, ProgressEvent, ReferenceMode, TextEntry
from .io_utils import list_voice_references, read_text_file
from .service import NarrationService

ASSET_DIR = Path(__file__).resolve().parent / "assets"
MODEL_LICENSE_URL = "https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt"

ColorValue = str | tuple[str, str]
COLORS: dict[str, ColorValue] = {
    "bg": ("#F4F4F6", "#0B0D20"),
    "bg_deep": ("#FFFFFF", "#060710"),
    "surface": ("#FFFFFF", "#121631"),
    "surface_strong": ("#ECEAF8", "#1A1F42"),
    "border": ("#DAD8E8", "#272D59"),
    "text": ("#17162A", "#F5F4FF"),
    "muted": ("#66657A", "#B9BBD1"),
    "accent": ("#6941C6", "#9D72EF"),
    "accent_hover": ("#7B55D1", "#B993FF"),
    "success": ("#178B62", "#55D6A3"),
    "danger": ("#C23B55", "#EF7C8E"),
}

MODE_LABELS = {
    "Uma voz": ReferenceMode.SINGLE,
    "Combinar amostras": ReferenceMode.COMBINE,
    "Comparar vozes": ReferenceMode.PER_REFERENCE,
}


class NarratorApp(ctk.CTk):
    """Janela principal para preparar, gerar e acompanhar narrações."""

    def __init__(self) -> None:
        """Carrega preferências e constrói a interface sem iniciar o modelo."""
        self.initial_theme = os.getenv("NINJA_NARRATOR_THEME", "dark").lower()
        if self.initial_theme not in {"dark", "light"}:
            self.initial_theme = "dark"
        ctk.set_appearance_mode(self.initial_theme)
        super().__init__(fg_color=COLORS["bg"])
        self.config_data: NarratorConfig = load_config()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancellation = threading.Event()
        self.last_output: Path | None = None
        self.voice_tokens: dict[str, str] = {}

        self.title("NinjaSoft Narrator")
        self.geometry("1180x820")
        self.minsize(1020, 720)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._create_variables()
        self._build_sidebar()
        self._build_workspace()
        self._refresh_voices()
        self.after(120, self._drain_events)

    def _create_variables(self) -> None:
        """Centraliza o estado editável dos controles."""
        mode_label = next(
            (
                label
                for label, mode in MODE_LABELS.items()
                if mode is self.config_data.reference_mode
            ),
            "Uma voz",
        )
        self.title_var = ctk.StringVar(value="minha_narracao")
        self.reference_dir_var = ctk.StringVar(value=str(self.config_data.reference_dir))
        self.output_dir_var = ctk.StringVar(value=str(self.config_data.output_dir))
        self.mode_var = ctk.StringVar(value=mode_label)
        self.voice_var = ctk.StringVar(value="Nenhuma voz encontrada")
        self.speed_var = ctk.DoubleVar(value=self.config_data.speed)
        self.duration_var = ctk.StringVar(
            value=""
            if self.config_data.target_duration is None
            else str(self.config_data.target_duration)
        )
        self.theme_var = ctk.StringVar(value=self.initial_theme)
        self.voice_authorized_var = ctk.BooleanVar(value=False)
        self.license_accepted_var = ctk.BooleanVar(value=False)
        self.status_var = ctk.StringVar(value="Pronto para configurar uma narração")

    def _build_sidebar(self) -> None:
        """Monta a faixa de marca e o resumo do fluxo."""
        sidebar = ctk.CTkFrame(self, width=252, corner_radius=0, fg_color=COLORS["bg_deep"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(8, weight=1)

        dark_path = ASSET_DIR / "ninjasoft-logo.png"
        light_path = ASSET_DIR / "ninjasoft-logo-light.png"
        if dark_path.exists():
            dark_logo = Image.open(dark_path)
            light_logo = Image.open(light_path) if light_path.exists() else dark_logo
            height = max(32, min(72, round(dark_logo.height * 178 / dark_logo.width)))
            self.logo_image = ctk.CTkImage(
                light_image=light_logo, dark_image=dark_logo, size=(178, height)
            )
            ctk.CTkLabel(sidebar, text="", image=self.logo_image).grid(
                row=0, column=0, padx=30, pady=(34, 8), sticky="w"
            )

        ctk.CTkLabel(
            sidebar,
            text="NINJASOFT NARRATOR",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["accent"],
        ).grid(row=1, column=0, padx=31, pady=(0, 36), sticky="w")
        ctk.CTkLabel(
            sidebar,
            text="FLUXO DE TRABALHO",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["muted"],
        ).grid(row=2, column=0, padx=31, pady=(0, 12), sticky="w")
        for row, (number, label) in enumerate(
            (
                ("01", "Escreva o texto"),
                ("02", "Escolha a voz"),
                ("03", "Ajuste a narração"),
                ("04", "Gere e escute"),
            ),
            start=3,
        ):
            self._add_workflow_step(sidebar, row, number, label)

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=9, column=0, padx=30, pady=28, sticky="sew")
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer, text="Tema claro", font=ctk.CTkFont(size=12), text_color=COLORS["muted"]
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkSwitch(
            footer,
            text="",
            width=38,
            variable=self.theme_var,
            onvalue="light",
            offvalue="dark",
            command=self._toggle_theme,
            progress_color=COLORS["accent"],
        ).grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(
            footer,
            text="Open source · execução local",
            font=ctk.CTkFont(size=10),
            text_color="#777B9A",
        ).grid(row=1, column=0, columnspan=2, pady=(18, 0), sticky="w")

    @staticmethod
    def _add_workflow_step(parent: ctk.CTkFrame, row: int, number: str, label: str) -> None:
        """Adiciona uma etapa compacta à lateral."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, padx=28, pady=7, sticky="ew")
        ctk.CTkLabel(
            frame,
            text=number,
            width=30,
            height=30,
            corner_radius=9,
            fg_color=COLORS["surface_strong"],
            text_color=COLORS["accent"],
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=0)
        ctk.CTkLabel(frame, text=label, text_color=COLORS["muted"], font=ctk.CTkFont(size=12)).grid(
            row=0, column=1, padx=(12, 0), sticky="w"
        )

    @staticmethod
    def _new_card(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
        """Cria um cartão visual consistente."""
        return ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
        )

    @staticmethod
    def _add_card_title(card: ctk.CTkFrame, title: str, subtitle: str) -> None:
        """Adiciona título e contexto a um cartão."""
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, padx=22, pady=(20, 0), sticky="w")
        ctk.CTkLabel(
            card,
            text=subtitle,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, padx=22, pady=(3, 0), sticky="w")

    def _build_workspace(self) -> None:
        """Monta os cartões de texto, voz, ajustes e execução."""
        workspace = ctk.CTkScrollableFrame(
            self,
            corner_radius=0,
            fg_color=COLORS["bg"],
            scrollbar_button_color=COLORS["surface_strong"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(workspace, fg_color="transparent")
        header.grid(row=0, column=0, padx=34, pady=(30, 20), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Narração local com IA",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Clone uma voz autorizada e transforme textos em áudio no seu computador.",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, pady=(5, 0), sticky="w")
        ctk.CTkLabel(
            header,
            text="PRIVACIDADE LOCAL",
            width=126,
            height=28,
            corner_radius=14,
            fg_color=COLORS["surface_strong"],
            text_color=COLORS["accent"],
            font=ctk.CTkFont(size=9, weight="bold"),
        ).grid(row=0, column=1, rowspan=2, padx=(20, 0), sticky="e")

        self._build_text_card(workspace)
        options = ctk.CTkFrame(workspace, fg_color="transparent")
        options.grid(row=2, column=0, padx=34, pady=(0, 18), sticky="ew")
        options.grid_columnconfigure((0, 1), weight=1, uniform="options")
        self._build_voice_card(options)
        self._build_settings_card(options)
        self._build_execution_card(workspace)

    def _build_text_card(self, parent: ctk.CTkBaseClass) -> None:
        """Cria o editor do conteúdo que será narrado."""
        card = self._new_card(parent)
        card.grid(row=1, column=0, padx=34, pady=(0, 18), sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        self._add_card_title(
            card, "Texto da narração", "Digite o conteúdo ou importe um arquivo TXT."
        )

        toolbar = ctk.CTkFrame(card, fg_color="transparent")
        toolbar.grid(row=2, column=0, padx=22, pady=(16, 8), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)
        self.title_entry = ctk.CTkEntry(
            toolbar,
            textvariable=self.title_var,
            height=40,
            corner_radius=10,
            fg_color=COLORS["bg_deep"],
            border_color=COLORS["border"],
            placeholder_text="Nome do arquivo de saída",
        )
        self.title_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            toolbar,
            text="Importar TXT",
            width=118,
            height=40,
            corner_radius=10,
            fg_color=COLORS["surface_strong"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            command=self._import_text,
        ).grid(row=0, column=1, padx=(10, 0))
        self.text_box = ctk.CTkTextbox(
            card,
            height=145,
            corner_radius=10,
            fg_color=COLORS["bg_deep"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=13),
            wrap="word",
        )
        self.text_box.grid(row=3, column=0, padx=22, pady=(0, 20), sticky="ew")
        self.text_box.insert(
            "1.0",
            "Bem-vindo ao NinjaSoft Narrator. Transforme este texto em uma narração natural, "
            "processada localmente com inteligência artificial.",
        )

    def _build_voice_card(self, parent: ctk.CTkFrame) -> None:
        """Cria a escolha da biblioteca, do modo e da voz."""
        card = self._new_card(parent)
        card.grid(row=0, column=0, padx=(0, 9), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        self._add_card_title(card, "Voz de referência", "Use somente amostras com autorização.")
        directory = ctk.CTkFrame(card, fg_color="transparent")
        directory.grid(row=2, column=0, padx=22, pady=(16, 10), sticky="ew")
        directory.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(
            directory,
            textvariable=self.reference_dir_var,
            height=38,
            fg_color=COLORS["bg_deep"],
            border_color=COLORS["border"],
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            directory,
            text="…",
            width=40,
            height=38,
            fg_color=COLORS["surface_strong"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            command=self._choose_reference_dir,
        ).grid(row=0, column=1, padx=(8, 0))
        self.mode_menu = ctk.CTkOptionMenu(
            card,
            values=list(MODE_LABELS),
            variable=self.mode_var,
            height=38,
            fg_color=COLORS["surface_strong"],
            button_color=COLORS["accent"],
            command=lambda _value: self._update_voice_state(),
        )
        self.mode_menu.grid(row=3, column=0, padx=22, pady=(0, 10), sticky="ew")
        self.voice_menu = ctk.CTkOptionMenu(
            card,
            values=["Nenhuma voz encontrada"],
            variable=self.voice_var,
            height=38,
            fg_color=COLORS["surface_strong"],
            button_color=COLORS["accent"],
        )
        self.voice_menu.grid(row=4, column=0, padx=22, pady=(0, 10), sticky="ew")
        ctk.CTkButton(
            card,
            text="Atualizar biblioteca",
            height=34,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["muted"],
            hover_color=COLORS["surface_strong"],
            command=self._refresh_voices,
        ).grid(row=5, column=0, padx=22, pady=(0, 20), sticky="ew")

    def _build_settings_card(self, parent: ctk.CTkFrame) -> None:
        """Cria os ajustes de ritmo, duração e pasta de entrega."""
        card = self._new_card(parent)
        card.grid(row=0, column=1, padx=(9, 0), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        self._add_card_title(
            card, "Ajustes da narração", "Controle ritmo e duração final opcional."
        )

        speed_header = ctk.CTkFrame(card, fg_color="transparent")
        speed_header.grid(row=2, column=0, padx=22, pady=(16, 0), sticky="ew")
        speed_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(speed_header, text="Velocidade", text_color=COLORS["muted"]).grid(
            row=0, column=0, sticky="w"
        )
        self.speed_label = ctk.CTkLabel(
            speed_header, text=f"{self.speed_var.get():.2f}×", text_color=COLORS["accent"]
        )
        self.speed_label.grid(row=0, column=1, sticky="e")
        ctk.CTkSlider(
            card,
            from_=0.5,
            to=2.0,
            number_of_steps=30,
            variable=self.speed_var,
            progress_color=COLORS["accent"],
            command=self._show_speed,
        ).grid(row=3, column=0, padx=22, pady=(5, 13), sticky="ew")
        ctk.CTkEntry(
            card,
            textvariable=self.duration_var,
            height=38,
            fg_color=COLORS["bg_deep"],
            border_color=COLORS["border"],
            placeholder_text="Duração alvo em segundos (opcional)",
        ).grid(row=4, column=0, padx=22, pady=(0, 10), sticky="ew")
        output = ctk.CTkFrame(card, fg_color="transparent")
        output.grid(row=5, column=0, padx=22, pady=(0, 20), sticky="ew")
        output.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(
            output,
            textvariable=self.output_dir_var,
            height=38,
            fg_color=COLORS["bg_deep"],
            border_color=COLORS["border"],
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            output,
            text="…",
            width=40,
            height=38,
            fg_color=COLORS["surface_strong"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            command=self._choose_output_dir,
        ).grid(row=0, column=1, padx=(8, 0))

    def _build_execution_card(self, parent: ctk.CTkBaseClass) -> None:
        """Cria consentimentos, ações e painel de progresso."""
        card = self._new_card(parent)
        card.grid(row=3, column=0, padx=34, pady=(0, 34), sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        self._add_card_title(
            card,
            "Gerar áudio",
            "O XTTS-v2 e suas saídas são limitados a uso não comercial pela CPML.",
        )
        consent = ctk.CTkFrame(card, fg_color="transparent")
        consent.grid(row=2, column=0, padx=22, pady=(15, 8), sticky="ew")
        ctk.CTkCheckBox(
            consent,
            text="Tenho autorização para usar as amostras de voz selecionadas.",
            variable=self.voice_authorized_var,
            checkbox_width=20,
            checkbox_height=20,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkCheckBox(
            consent,
            text="Li e aceito a licença CPML do modelo XTTS-v2.",
            variable=self.license_accepted_var,
            checkbox_width=20,
            checkbox_height=20,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text"],
        ).grid(row=1, column=0, pady=(9, 0), sticky="w")
        ctk.CTkButton(
            consent,
            text="Ler licença",
            width=90,
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["accent"],
            hover_color=COLORS["surface_strong"],
            command=lambda: webbrowser.open(MODEL_LICENSE_URL),
        ).grid(row=1, column=1, padx=(12, 0), pady=(9, 0))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=3, column=0, padx=22, pady=(8, 10), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)
        self.generate_button = ctk.CTkButton(
            actions,
            text="Gerar narração",
            height=44,
            corner_radius=11,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_narration,
        )
        self.generate_button.grid(row=0, column=0, sticky="ew")
        self.cancel_button = ctk.CTkButton(
            actions,
            text="Cancelar",
            width=92,
            height=44,
            state="disabled",
            fg_color=COLORS["surface_strong"],
            hover_color=COLORS["border"],
            text_color=COLORS["danger"],
            command=self._cancel_narration,
        )
        self.cancel_button.grid(row=0, column=1, padx=(10, 0))
        ctk.CTkButton(
            actions,
            text="Ouvir último",
            width=106,
            height=44,
            fg_color=COLORS["surface_strong"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            command=self._play_last_output,
        ).grid(row=0, column=2, padx=(10, 0))
        ctk.CTkButton(
            actions,
            text="Abrir pasta",
            width=98,
            height=44,
            fg_color=COLORS["surface_strong"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            command=self._open_output_dir,
        ).grid(row=0, column=3, padx=(10, 0))

        self.progress_bar = ctk.CTkProgressBar(card, height=6, progress_color=COLORS["accent"])
        self.progress_bar.grid(row=4, column=0, padx=22, pady=(3, 8), sticky="ew")
        self.progress_bar.set(0)
        ctk.CTkLabel(
            card,
            textvariable=self.status_var,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=11),
        ).grid(row=5, column=0, padx=22, pady=(0, 8), sticky="w")
        self.log_box = ctk.CTkTextbox(
            card,
            height=92,
            corner_radius=10,
            fg_color=COLORS["bg_deep"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["muted"],
            font=ctk.CTkFont(family="Consolas", size=10),
            state="disabled",
        )
        self.log_box.grid(row=6, column=0, padx=22, pady=(0, 20), sticky="ew")

    def _toggle_theme(self) -> None:
        """Alterna o tema sem reconstruir os controles."""
        ctk.set_appearance_mode(self.theme_var.get())

    def _show_speed(self, value: float) -> None:
        """Atualiza o valor textual ligado ao controle de velocidade."""
        self.speed_label.configure(text=f"{value:.2f}×")

    def _import_text(self) -> None:
        """Importa um TXT e preserva seu nome como sugestão de saída."""
        path_value = filedialog.askopenfilename(
            title="Importar texto", filetypes=(("Arquivo de texto", "*.txt"),)
        )
        if not path_value:
            return
        path = Path(path_value)
        try:
            content = read_text_file(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Não foi possível importar", str(error), parent=self)
            return
        self.title_var.set(path.stem)
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", content)

    def _choose_reference_dir(self) -> None:
        """Seleciona a biblioteca de vozes e atualiza a lista."""
        selected = filedialog.askdirectory(
            title="Escolher biblioteca de vozes", initialdir=self.reference_dir_var.get()
        )
        if selected:
            self.reference_dir_var.set(selected)
            self._refresh_voices()

    def _choose_output_dir(self) -> None:
        """Seleciona o diretório de entrega dos arquivos WAV."""
        selected = filedialog.askdirectory(
            title="Escolher pasta de saída", initialdir=self.output_dir_var.get()
        )
        if selected:
            self.output_dir_var.set(selected)

    def _refresh_voices(self) -> None:
        """Recarrega as amostras e cria rótulos distintos para a interface."""
        references = list_voice_references(Path(self.reference_dir_var.get()).expanduser())
        self.voice_tokens.clear()
        labels = []
        for reference in references:
            label = reference.label
            if label in self.voice_tokens:
                label = f"{label} · {reference.relative_path.parent}"
            labels.append(label)
            self.voice_tokens[label] = reference.token
        if not labels:
            labels = ["Nenhuma voz encontrada"]
        self.voice_menu.configure(values=labels)
        self.voice_var.set(labels[0])
        self._update_voice_state()

    def _update_voice_state(self) -> None:
        """Habilita a escolha individual somente no modo compatível."""
        state = "normal" if MODE_LABELS[self.mode_var.get()] is ReferenceMode.SINGLE else "disabled"
        self.voice_menu.configure(state=state)

    def _build_request(self) -> NarrationRequest:
        """Valida os controles e cria uma solicitação imutável."""
        text = self.text_box.get("1.0", "end").strip()
        title = self.title_var.get().strip()
        if not title:
            raise ValueError("Informe um nome para a narração.")
        duration_text = self.duration_var.get().strip().replace(",", ".")
        target_duration = float(duration_text) if duration_text else None
        selected_token = self.voice_tokens.get(self.voice_var.get())
        request = NarrationRequest(
            entries=(TextEntry(name=title, text=text),),
            reference_dir=Path(self.reference_dir_var.get()).expanduser().resolve(),
            output_dir=Path(self.output_dir_var.get()).expanduser().resolve(),
            mode=MODE_LABELS[self.mode_var.get()],
            selected_reference=selected_token,
            speed=float(self.speed_var.get()),
            target_duration=target_duration,
            language=self.config_data.language,
            model_name=self.config_data.model_name,
            device=self.config_data.device,
            model_license_accepted=self.license_accepted_var.get(),
            voice_use_authorized=self.voice_authorized_var.get(),
        )
        request.validate()
        return request

    def _start_narration(self) -> None:
        """Inicia a síntese fora da thread gráfica."""
        if self.worker and self.worker.is_alive():
            return
        try:
            request = self._build_request()
        except (OSError, ValueError) as error:
            messagebox.showwarning("Revise a configuração", str(error), parent=self)
            return

        self.cancellation.clear()
        self.generate_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.status_var.set("Preparando o modelo local…")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self._append_log("Narração iniciada.")
        self.worker = threading.Thread(
            target=self._run_narration, args=(request,), daemon=True, name="narration-worker"
        )
        self.worker.start()

    def _run_narration(self, request: NarrationRequest) -> None:
        """Executa o serviço e envia eventos seguros para a thread gráfica."""
        try:
            result = NarrationService().narrate(
                request,
                progress_callback=lambda event: self.events.put(("progress", event)),
                cancellation=self.cancellation,
            )
        except Exception as error:
            self.events.put(("error", error))
        else:
            self.events.put(("result", result))

    def _cancel_narration(self) -> None:
        """Solicita cancelamento entre etapas de síntese."""
        self.cancellation.set()
        self.cancel_button.configure(state="disabled")
        self.status_var.set("Cancelamento solicitado; concluindo a etapa atual…")

    def _drain_events(self) -> None:
        """Aplica na interface os eventos produzidos pelo worker."""
        try:
            while True:
                event_type, payload = self.events.get_nowait()
                if event_type == "progress":
                    progress = payload
                    if isinstance(progress, ProgressEvent):
                        self.status_var.set(progress.message)
                        self._append_log(progress.message)
                elif event_type == "result":
                    self._finish_narration(payload)
                elif event_type == "error":
                    self._fail_narration(payload)
        except queue.Empty:
            pass
        self.after(120, self._drain_events)

    def _finish_narration(self, result: object) -> None:
        """Restaura os controles e apresenta o resumo final."""
        self._reset_execution_controls()
        generated = getattr(result, "generated", [])
        failures = getattr(result, "failures", [])
        cancelled = getattr(result, "cancelled", False)
        if generated:
            self.last_output = generated[-1].path
        if cancelled:
            self.status_var.set("Narração cancelada.")
        elif failures:
            self.status_var.set(f"Concluído com {len(failures)} falha(s).")
        else:
            self.status_var.set(f"Concluído: {len(generated)} áudio(s) gerado(s).")

    def _fail_narration(self, error: object) -> None:
        """Exibe uma falha não recuperável e libera uma nova tentativa."""
        self._reset_execution_controls()
        self.status_var.set("Não foi possível concluir a narração.")
        self._append_log(f"Erro: {error}")
        messagebox.showerror("Erro na narração", str(error), parent=self)

    def _reset_execution_controls(self) -> None:
        """Interrompe o progresso e reativa as ações principais."""
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1)
        self.generate_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

    def _append_log(self, message: str) -> None:
        """Acrescenta uma linha ao painel de atividade."""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    @staticmethod
    def _open_path(path: Path) -> None:
        """Abre arquivo ou diretório com o aplicativo padrão do sistema."""
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _open_output_dir(self) -> None:
        """Cria e abre a pasta configurada para os resultados."""
        output_dir = Path(self.output_dir_var.get()).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        self._open_path(output_dir)

    def _play_last_output(self) -> None:
        """Reproduz o áudio mais recente no player padrão."""
        if not self.last_output or not self.last_output.exists():
            messagebox.showinfo(
                "Nenhum áudio disponível",
                "Gere uma narração antes de usar esta ação.",
                parent=self,
            )
            return
        self._open_path(self.last_output)

    def _on_close(self) -> None:
        """Confirma o fechamento quando houver uma síntese em andamento."""
        if self.worker and self.worker.is_alive():
            confirmed = messagebox.askyesno(
                "Narração em andamento",
                "Deseja solicitar o cancelamento e fechar a interface?",
                parent=self,
            )
            if not confirmed:
                return
            self.cancellation.set()
        self.destroy()


def main() -> None:
    """Inicia a aplicação desktop."""
    app = NarratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
