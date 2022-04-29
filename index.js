class Message {
    constructor(type,{
        channel= 	0,
        frame_type= 	0,
        frame_value= 	0,
        control= 	0,
        note=	0,
        program = 	0,
        song = 	0,
        value= 	0,
        velocity = 	64,
        data 	=[]	,
        pitch =0,
        pos 	= 	0,
        time =	0,
    }) {
        this.type = type;
        this.channel= 	channel;
        this.frame_type=frame_type;
        this.frame_value= 	frame_value;
        this.control= 	control;
        this.note=	note;
        this.program = 	program;
        this.song = 	song;
        this.value= 	value;
        this.velocity = 	velocity,
        this.data 	=data;
        this.pitch =pitch;
        this.pos 	= 	pos;
        this.time =	time;
    }
  };

class Output {
constructor(name="", autoreset=false) {
}
close() {}

get is_input() {return false;}

get is_output() {return true;}

panic() {
/**
 * TODO
 * Send “All Sounds Off” on all channels.
 * This will mute all sounding notes regardless of envelopes. Useful when notes are hanging and nothing else helps.
 */
}

reset() {
/**
 * TODO
 * Send “All Notes Off” and “Reset All Controllers” on all channels
 */
}

send(msg) {
    console.log(msg);
}
}

const mido = {
  Message,
  Output,
  open_output: function(name=undefined, {virtual=false, autoreset=false}) {
    return new Output(name, autoreset);
  },
  open_input: function(name=undefined, {virtual=false, autoreset=false}) {}
};

class MidiPlayer {
    constructor(midi_output) {
        this.output = midi_output;
    }

    send(message, timestamp) {
        const bytes = [...message.bytes()].map(b => Number(b));
        console.log(bytes, timestamp);
        this.output.send(bytes, timestamp);
    }

    static async create() {
        const midiAccess = await navigator.requestMIDIAccess();
        console.log(midiAccess.outputs);
        const output = [...midiAccess.outputs].filter(([,{name}]) => name === "IAC-Treiber IAC-Bus 2")[0]?.[1];
        await output.open();
        return new MidiPlayer(output);
   }
}

const midi_player = {
    MidiPlayer
}

async function main(){
    const p = new Promise((resolve)=>{
        window.launch_super_mega_hack = () => {
            resolve();
            return "Launching PROOF OF CONCEPT!";
        }
    })
    await p;

    const sleep = async (t) => new Promise((resolve) => {setTimeout(resolve, t);});

    await sleep(500);
    console.log("HACK!");
    await sleep(500);
    console.log("  HACK!");
    await sleep(500);
    console.log("    HACK!");
    console.log();

    let pyodide = await loadPyodide();

    await pyodide.loadPackage(["micropip", "numpy", "scipy"]);

    pyodide.registerJsModule("midi_player", midi_player);

    await pyodide.runPythonAsync(`
      import micropip
      await micropip.install('mido')
      import mido
    `);

    await pyodide.runPythonAsync(`
        import os
        from pyodide.http import pyfetch

        os.mkdir("basismixer");

        response = await pyfetch("./basismixer/performance_codec.py")
        with open("basismixer/performance_codec.py", "wb") as f:
            f.write(await response.bytes())

        response = await pyfetch("./basismixer/expression_tools.py")
        with open("basismixer/expression_tools.py", "wb") as f:
            f.write(await response.bytes())

        response = await pyfetch("./basismixer/bm_utils.py")
        with open("basismixer/bm_utils.py", "wb") as f:
            f.write(await response.bytes())

        response = await pyfetch("./midi_thread.py")
        with open("midi_thread.py", "wb") as f:
            f.write(await response.bytes())

        response = await pyfetch("./leap_control.py")
        with open("leap_control.py", "wb") as f:
            f.write(await response.bytes())

        os.mkdir("bm_files");

        response = await pyfetch("./bm_files/beethoven_fuer_elise_complete.json")
        with open("bm_files/beethoven_fuer_elise_complete.json", "wb") as f:
            f.write(await response.bytes())
        response = await pyfetch("./bm_files/beethoven_fuer_elise_complete.pedal")
        with open("bm_files/beethoven_fuer_elise_complete.pedal", "wb") as f:
            f.write(await response.bytes())
        response = await pyfetch("./bm_files/beethoven_fuer_elise_complete.txt")
        with open("bm_files/beethoven_fuer_elise_complete.txt", "wb") as f:
            f.write(await response.bytes())
    `);

    window.midi_player = await MidiPlayer.create();

    pyodide.runPython(`
        import js
        from leap_control import LeapControl

        CONFIG = {'playmode': 'BM',
                  'control': 'Mouse',
                  'bm_file': 'bm_files/beethoven_op027_no2_mv1_bm_z.txt',
                  'bm_config': 'bm_files/beethoven_op027_no2_mv1_bm_z.json'}

        SONG_LIST = ['bm_files/beethoven_fuer_elise_complete.txt']


        # instantiate LeapControl
        lc = LeapControl(CONFIG, SONG_LIST, js.midi_player)
        lc.play()
    `);
}

main();
