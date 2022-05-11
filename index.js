// Utility function to load a SoundFont file from a URL using XMLHttpRequest.
// The same origin policy will apply, as for all XHR requests.
function loadSoundFont(url, success, error) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.responseType = "arraybuffer";
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                success(new Uint8Array(xhr.response));
            } else {
                if (options.error) {
                    options.error(xhr.statusText);
                }
            }
        }
    };
    xhr.send();
}

// Load and parse a SoundFont file.
loadSoundFont("Yamaha-Grand-Lite-v2.0.sf3", async function (sf2Data) {
    await JSSynth.waitForReady();

    // Prepare the AudioContext instance
    var context = new AudioContext();
    setInterval(()=>context.resume(), 1000);

    await context.audioWorklet.addModule('./libfluidsynth-2.2.1-sf3.js')
    await context.audioWorklet.addModule('https://unpkg.com/js-synthesizer@1.8.4/dist/js-synthesizer.worklet.js');

    // Create the synthesizer instance for AudioWorkletNode
    window.synth = new JSSynth.AudioWorkletNodeSynthesizer();
    synth.init(context.sampleRate);
    // You must create AudioWorkletNode before using other methods
    // (This is because the message port is not available until the
    // AudioWorkletNode is created)
    const audioNode = synth.createAudioNode(context);
    audioNode.connect(context.destination); // or another node...
    // After node creation, you can use Synthesizer methods
    await synth.loadSFont(sf2Data);

    // Load your SoundFont data (sfontBuffer: ArrayBuffer)
    window.sfId = await synth.loadSFont(sf2Data);
    window.synth = synth;

    console.log("Sound font loaded");
});

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
    constructor() {
    }

    send(message, timestamp) {
        const dict = message.dict();
        const bytes = [...message.bytes()].map(b => Number(b));
        try {
            switch(dict.get('type')) {
                case "note_on":
                    console.log("note_on", message.note, message.velocity);
                    synth.midiNoteOn(Number(message.channel), Number(message.note), Number(message.velocity));
                    break;
                case "note_off":
                    console.log("note_off", message.note);
                    synth.midiNoteOn(Number(message.channel), Number(message.note));
                    break;
                case "control_change":
                    if(message.channel === 0) {
                        console.log("control_change", message.channel, message.control, message.value);
                        synth.midiControl(Number(message.channel), Number(message.control), Number(message.value));
                    }
                    break;
            }
        } catch(e) {
            console.log(e);
        }
    }

    static async create() {
        return new MidiPlayer();
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
