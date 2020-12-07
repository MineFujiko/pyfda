# -*- coding: utf-8 -*-
#
# This file is part of the pyFDA project hosted at https://github.com/chipmuenk/pyfda
#
# Copyright © pyFDA Project Contributors
# Licensed under the terms of the MIT License
# (see file LICENSE in root directory for details)

"""
Subwidget for entering frequency units
"""
import sys
import logging
logger = logging.getLogger(__name__)

from pyfda.libs.compat import (QtCore,
                      QWidget, QLabel, QLineEdit, QComboBox, QFrame, QFont, QToolButton,
                      QIcon, QVBoxLayout, QHBoxLayout, QGridLayout,
                      pyqtSignal, QEvent)


import pyfda.filterbroker as fb
from pyfda.libs.pyfda_lib import to_html, safe_eval
from pyfda.libs.pyfda_qt_lib import qget_cmb_box
from pyfda.pyfda_rc import params # FMT string for QLineEdit fields, e.g. '{:.3g}'


class FreqUnits(QWidget):
    """
    Build and update widget for entering frequency unit, frequency range and
    sampling frequency f_S

    The following key-value pairs of the `fb.fil[0]` dict are modified:

        - `'freq_specs_unit'` : The unit ('k', 'f_S', 'f_Ny', 'Hz' etc.) as a string
        - `'freqSpecsRange'` : A list with two entries for minimum and maximum frequency
                               values for labelling the frequency axis
        - `'f_S'` : The sampling frequency for referring frequency values to as a float
        - `'f_max'` : maximum frequency for scaling frequency axis
        - `'plt_fUnit'`: frequency unit as string
        - `'plt_tUnit'`: time unit as string
        - `'plt_fLabel'`: label for frequency axis
        - `'plt_tLabel'`: label for time axis

    """

    # class variables (shared between instances if more than one exists)
    sig_tx = pyqtSignal(object) # outgoing

    def __init__(self, parent, title = "Frequency Units"):

        super(FreqUnits, self).__init__(parent)
        self.title = title
        self.spec_edited = False # flag whether QLineEdit field has been edited

        self._construct_UI()

    def _construct_UI(self):
        """
        Construct the User Interface
        """
        self.layVMain = QVBoxLayout() # Widget main layout

        f_units = ['k','f_S', 'f_Ny', 'Hz', 'kHz', 'MHz', 'GHz']
        self.t_units = ['', '', '', 's', 'ms', r'$\mu$s', 'ns']

        bfont = QFont()
        bfont.setBold(True)

        self.lblUnits=QLabel(self)
        self.lblUnits.setText("Freq. Unit")
        self.lblUnits.setFont(bfont)

        self.fs_old = fb.fil[0]['f_S'] # store current sampling frequency

        self.lblF_S = QLabel(self)
        self.lblF_S.setText(to_html("f_S =", frmt='bi'))

        self.ledF_S = QLineEdit()
        self.ledF_S.setText(str(fb.fil[0]["f_S"]))
        self.ledF_S.setObjectName("f_S")
        self.ledF_S.installEventFilter(self)  # filter events
        
        self.butLock = QToolButton(self)
        self.butLock.setIcon(QIcon(':/lock-locked.svg'))
        self.butLock.setCheckable(True)
        self.butLock.setChecked(True)
        self.butLock.setToolTip("Lock frequencies to sampling frequency; when f_S changes, "
                                "all frequencies are scaled to f_S.")
        #self.butLock.setStyleSheet("QToolButton:checked {font-weight:bold}")
        
        layHF_S = QHBoxLayout()
        layHF_S.addWidget(self.ledF_S)
        layHF_S.addWidget(self.butLock)

        self.cmbUnits = QComboBox(self)
        self.cmbUnits.setObjectName("cmbUnits")
        self.cmbUnits.addItems(f_units)
        self.cmbUnits.setToolTip(
        'Select whether frequencies are specified w.r.t. \n'
        'the sampling frequency "f_S", to the Nyquist frequency \n'
        'f_Ny = f_S/2 or as absolute values. "k" specifies frequencies w.r.t. f_S '
        'but plots graphs over the frequency index k.')
        self.cmbUnits.setCurrentIndex(1)
#        self.cmbUnits.setItemData(0, (0,QColor("#FF333D"),Qt.BackgroundColorRole))#
#        self.cmbUnits.setItemData(0, (QFont('Verdana', bold=True), Qt.FontRole)

        fRanges = [("0...½", "half"), ("0...1","whole"), ("-½...½", "sym")]
        self.cmbFRange = QComboBox(self)
        self.cmbFRange.setObjectName("cmbFRange")
        for f in fRanges:
            self.cmbFRange.addItem(f[0],f[1])
        self.cmbFRange.setToolTip("Select frequency range (whole or half).")
        self.cmbFRange.setCurrentIndex(0)

        # Combobox resizes with longest entry
        self.cmbUnits.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cmbFRange.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        self.butSort = QToolButton(self)
        self.butSort.setText("Sort")
        self.butSort.setIcon(QIcon(':/sort-ascending.svg'))
        #self.butDelCells.setIconSize(q_icon_size)
        self.butSort.setCheckable(True)
        self.butSort.setChecked(True)
        self.butSort.setToolTip("Sort frequencies in ascending order when pushed.")
        self.butSort.setStyleSheet("QToolButton:checked {font-weight:bold}")

        self.layHUnits = QHBoxLayout()
        self.layHUnits.addWidget(self.cmbUnits)
        self.layHUnits.addWidget(self.cmbFRange)
        self.layHUnits.addWidget(self.butSort)

        # Create a gridLayout consisting of QLabel and QLineEdit fields
        # for setting f_S, the units and the actual frequency specs:
        self.layGSpecWdg = QGridLayout() # sublayout for spec fields
        self.layGSpecWdg.addWidget(self.lblF_S,1,0)
        # self.layGSpecWdg.addWidget(self.ledF_S,1,1)
        self.layGSpecWdg.addLayout(layHF_S,1,1)
        self.layGSpecWdg.addWidget(self.lblUnits,0,0)
        self.layGSpecWdg.addLayout(self.layHUnits,0,1)

        frmMain = QFrame(self)
        frmMain.setLayout(self.layGSpecWdg)

        self.layVMain.addWidget(frmMain)
        self.layVMain.setContentsMargins(*params['wdg_margins'])

        self.setLayout(self.layVMain)

        #----------------------------------------------------------------------
        # LOCAL SIGNALS & SLOTs
        #----------------------------------------------------------------------
        self.cmbUnits.currentIndexChanged.connect(self.update_UI)
        self.butLock.clicked.connect(self.update_UI)
        self.cmbFRange.currentIndexChanged.connect(self._freq_range)
        self.butSort.clicked.connect(self._store_sort_flag)
        #----------------------------------------------------------------------

        self.update_UI() # first-time initialization

#-------------------------------------------------------------
    def lock_fs(self):
        """
        Lock / unlock the sampling frequency: The current sampling frequency is
        stored in `fb.fil[0]['f_S']`. This frequency is used by frequency related
        widgets to scale absolute frequencies and store the values in normalized
        form. When the sampling frequency changes, absolute frequencies change
        their values. Most of the time, this is the desired behaviour, the properties
        of a system or a signal are defined by the normalized frequencies.
        
        When the effect of varying the sampling frequency is to be analyzed, the
        current value of `f_S` can be locked as `fb.fil[0]['f_S_locked']`
        by pressing the Lock button. Widgets can then use this value for scaling
        the normalized frequencies.
            
        - When the button is locked, the current sampling frequency is frozen
          in  `fb.fil[0]['f_S_locked']`
        - When the button is unlocked, the dictionary entry is replaced by 
          `None`. Frequency related widgets are forced to use the current
          `f_S` setting.
        """

        if self.butLock.isChecked():
            # Lock has been activated, store current f_S
            fb.fil[0].update({'f_S_locked':fb.fil[0]['f_S']})
            self.butLock.setIcon(QIcon(':/lock-locked.svg'))
        else:
            # Lock has been unlocked, replace old f_S setting by None
            fb.fil[0].update({'f_S_locked':None})
            self.butLock.setIcon(QIcon(':/lock-unlocked.svg'))

        self.sig_tx.emit({'sender':__name__, 'view_changed':'f_unit'})

#-------------------------------------------------------------
    def update_UI(self):
        """
        Transform the displayed frequency spec input fields according to the units
        setting. Spec entries are always stored normalized w.r.t. f_S in the
        dictionary; when f_S or the unit are changed, only the displayed values
        of the frequency entries are updated, not the dictionary!
        Signals are blocked before changing the value for f_S programmatically

        update_UI is called
        - during init
        - when the unit combobox is changed

        Update the freqSpecsRange and finally, emit 'view_changed' signal
        """
        f_unit = str(self.cmbUnits.currentText()) # selected frequency unit
        
        is_normalized_freq = f_unit in  {"f_S", "f_Ny", "k"}

        self.ledF_S.setVisible(not is_normalized_freq) # only vis. when
        self.lblF_S.setVisible(not is_normalized_freq) # not normalized
        self.butLock.setVisible(not is_normalized_freq)#
        f_S_scale = 1 # default setting for f_S scale

        if is_normalized_freq:
            self.fs_old = fb.fil[0]['f_S'] # store current sampling frequency
            t_label = r"$n \; \rightarrow$"

            if f_unit == "f_S": # normalized to f_S
                fb.fil[0]['f_S'] = fb.fil[0]['f_max'] = 1.
                fb.fil[0]['T_S'] = 1.
                f_label = r"$F = f\, /\, f_S = \Omega \, /\,  2 \mathrm{\pi} \; \rightarrow$"
            elif f_unit == "f_Ny":  # normalized to f_nyq = f_S / 2
                fb.fil[0]['f_S'] = fb.fil[0]['f_max'] = 2.
                fb.fil[0]['T_S'] = 1.
                f_label = r"$F = 2f \, / \, f_S = \Omega \, / \, \mathrm{\pi} \; \rightarrow$"
            else: # frequency index k, 
                fb.fil[0]['f_S'] = 1.
                fb.fil[0]['T_S'] = 1.
                fb.fil[0]['f_max'] = params['N_FFT']
                f_label = r"$k \; \rightarrow$"

            self.ledF_S.setText(params['FMT'].format(fb.fil[0]['f_S']))

        else: # Hz, kHz, ...
            # Restore sampling frequency when returning from f_S / f_Ny / k
            if fb.fil[0]['freq_specs_unit'] in {"f_S", "f_Ny", "k"}: # previous setting normalized?
                fb.fil[0]['f_S'] = fb.fil[0]['f_max'] = self.fs_old # yes, restore prev.
                fb.fil[0]['T_S'] = 1./self.fs_old # settings for sampling frequency
                self.ledF_S.setText(params['FMT'].format(fb.fil[0]['f_S']))

            if f_unit == "Hz":
                f_S_scale = 1.
            elif f_unit == "kHz":
                f_S_scale = 1.e3
            elif f_unit == "MHz":
                f_S_scale = 1.e6
            elif f_unit == "GHz":
                f_S_scale = 1.e9
            else:
                logger.warning("Unknown frequency unit {0}".format(f_unit))

            f_label = r"$f$ in " + f_unit + r"$\; \rightarrow$"
            idx = self.cmbUnits.currentIndex() # read index of units combobox
            t_label = r"$t$ in " + self.t_units[idx] + r"$\; \rightarrow$"

        if f_unit == "k":
            plt_f_unit = "f_S"
        else:
            plt_f_unit = f_unit

        fb.fil[0].update({'f_S_scale':f_S_scale}) # scale factor for f_S (Hz, kHz, ...)

# =============================================================================
#         if self.butLock.isChecked():
#             fb.fil[0].update({'f_S_locked':fb.fil[0]['f_S']}) # f_S locked, store old fs here or none?
#             self.butLock.setIcon(QIcon(':/lock-locked.svg'))
#         else:
#             fb.fil[0].update({'f_S_locked':None}) # f_S locked, store old fs here or none? 
#             self.butLock.setIcon(QIcon(':/lock-unlocked.svg'))
#         # the unit or label that is selected in the combo box
# =============================================================================
        fb.fil[0].update({'freq_specs_unit':f_unit}) # frequency unit
        # time and frequency unit as string e.g. for plot axis labeling
        fb.fil[0].update({"plt_fUnit":plt_f_unit}) 
        fb.fil[0].update({"plt_tUnit":self.t_units[idx]}) 
        # complete plot axis labels including unit and arrow
        fb.fil[0].update({"plt_fLabel":f_label})
        fb.fil[0].update({"plt_tLabel":t_label})

        self._freq_range(emit=False) # update f_lim setting without emitting signal

        self.sig_tx.emit({'sender':__name__, 'view_changed':'f_unit'})

#------------------------------------------------------------------------------

    def eventFilter(self, source, event):

        """
        Filter all events generated by the QLineEdit widgets. Source and type
        of all events generated by monitored objects are passed to this eventFilter,
        evaluated and passed on to the next hierarchy level.

        - When a QLineEdit widget gains input focus (QEvent.FocusIn`), display
          the stored value from filter dict with full precision
        - When a key is pressed inside the text field, set the `spec_edited` flag
          to True.
        - When a QLineEdit widget loses input focus (QEvent.FocusOut`), store
          current value with full precision (only if `spec_edited`== True) and
          display the stored value in selected format. Emit 'view_changed':'f_S'
        """
        def _store_entry():
            """
            Update filter dictionary, set line edit entry with reduced precision
            again.
            """
            if self.spec_edited:
                fb.fil[0].update({'f_S':safe_eval(source.text(), fb.fil[0]['f_S'], sign='pos')})
                fb.fil[0].update({'T_S':1./fb.fil[0]['f_S']})
                fb.fil[0].update({'f_max':fb.fil[0]['f_S']})

                self._freq_range(emit = False) # update plotting range
                self.sig_tx.emit({'sender':__name__, 'view_changed':'f_S'})
                self.spec_edited = False # reset flag, changed entry has been saved

        if source.objectName() == 'f_S':
            if event.type() == QEvent.FocusIn:
                self.spec_edited = False
                source.setText(str(fb.fil[0]['f_S'])) # full precision
            elif event.type() == QEvent.KeyPress:
                self.spec_edited = True # entry has been changed
                key = event.key()
                if key in {QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter}:
                    _store_entry()
                elif key == QtCore.Qt.Key_Escape: # revert changes
                    self.spec_edited = False
                    source.setText(str(fb.fil[0]['f_S'])) # full precision

            elif event.type() == QEvent.FocusOut:
                _store_entry()
                source.setText(params['FMT'].format(fb.fil[0]['f_S'])) # reduced precision
        # Call base class method to continue normal event processing:
        return super(FreqUnits, self).eventFilter(source, event)

    #-------------------------------------------------------------
    def _freq_range(self, emit = True):
        """
        Set frequency plotting range for single-sided spectrum up to f_S/2 or f_S
        or for double-sided spectrum between -f_S/2 and f_S/2

        Emit 'view_changed':'f_range' when `emit=True`
        """
        if type(emit) == int: # signal was emitted by combobox
            emit = True

        rangeType = qget_cmb_box(self.cmbFRange)

        fb.fil[0].update({'freqSpecsRangeType':rangeType})
        f_max = fb.fil[0]["f_max"]

        if rangeType == 'whole':
            f_lim = [0, f_max]
        elif rangeType == 'sym':
            f_lim = [-f_max/2., f_max/2.]
        else:
            f_lim = [0, f_max/2.]

        fb.fil[0]['freqSpecsRange'] = f_lim # store settings in dict

        if emit:
            self.sig_tx.emit({'sender':__name__, 'view_changed':'f_range'})

    #-------------------------------------------------------------
    def load_dict(self):
        """
        Reload comboBox settings and textfields from filter dictionary
        Block signals during update of combobox / lineedit widgets
        """
        self.ledF_S.setText(params['FMT'].format(fb.fil[0]['f_S']))

        self.cmbUnits.blockSignals(True)
        idx = self.cmbUnits.findText(fb.fil[0]['freq_specs_unit']) # get and set
        self.cmbUnits.setCurrentIndex(idx) # index for freq. unit combo box
        self.cmbUnits.blockSignals(False)

        self.cmbFRange.blockSignals(True)
        idx = self.cmbFRange.findData(fb.fil[0]['freqSpecsRangeType'])
        self.cmbFRange.setCurrentIndex(idx) # set frequency range
        self.cmbFRange.blockSignals(False)

        self.butSort.blockSignals(True)
        self.butSort.setChecked(fb.fil[0]['freq_specs_sort'])
        self.butSort.blockSignals(False)

#-------------------------------------------------------------
    def _store_sort_flag(self):
        """
        Store sort flag in filter dict and emit 'specs_changed':'f_sort'
        when sort button is checked.
        """
        fb.fil[0]['freq_specs_sort'] = self.butSort.isChecked()
        if self.butSort.isChecked():
            self.sig_tx.emit({'sender':__name__, 'specs_changed':'f_sort'})

#------------------------------------------------------------------------------

if __name__ == '__main__':

    from pyfda.libs.compat import QApplication
    app = QApplication(sys.argv)
    form = FreqUnits(None)

    form.update_UI()
#    form.updateUI(newLabels = ['F_PB','F_PB2'])

    form.show()

    app.exec_()
